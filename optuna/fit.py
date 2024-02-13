import optuna
import jax
import jax.numpy as jnp
from jax.experimental import sparse
from flax import linen as nn
import numpy as np
import optax
from typing import Collection, Callable, Optional

# We generate some toy data, 1000 sets each with a size drawn from
# an exponential distribution. The maximum size is fixed to 400.
# Each set has elements which are vectors of size two.
rng = np.random.default_rng(1)


def generate(rng, size):
    n = rng.exponential(size=size)
    n *= 400 / np.max(n)
    n += 1  # ensure there are no empty sets
    n = n.astype(int)

    # The mapping to learn is a non-linear function of the inputs. One can also
    # replace np.mean with np.max or np.sum.
    def true_mapping(x):
        return np.log1p(np.abs(np.sum(x[:, 0] ** 2 + 3 * x[:, 1])))

    X = [np.array(rng.normal(size=(ni, 2)), dtype=np.float32) for ni in n]
    y = [true_mapping(x) for x in X]

    return X, y


def preprocess(X, y, padded_X_size, padded_y_size, dtype=np.float32):
    """
    Concatenates the input sets and pads inputs and outputs to fixed sizes.

    Returns padded arrays, the summation matrix, and a mask to undo the padding.
    """
    assert padded_y_size >= len(y)
    n = [len(x) for x in X]
    mask = np.zeros(padded_y_size, dtype=bool)
    mask[: len(y)] = 1
    assert padded_X_size >= np.sum(n)
    y = np.concatenate([y, np.zeros(padded_y_size - len(y), dtype=dtype)])
    X = np.concatenate(X, dtype=dtype)
    X = np.concatenate(
        [X, np.zeros((padded_X_size - len(X),) + X.shape[1:], dtype=dtype)]
    )
    indices = np.empty((np.sum(n), 2), dtype=int)
    a = 0
    for j, b in enumerate(np.cumsum(n)):
        indices[a:b, 0] = j
        indices[a:b, 1] = np.arange(a, b)
        a = b
    sum_matrix = sparse.BCOO(
        (np.ones(len(indices), dtype=np.int8), indices),
        shape=(padded_y_size, padded_X_size),
        indices_sorted=True,
        unique_indices=True,
    )
    print(
        f"X fractional overhead {np.mean(np.sum(sum_matrix.todense(), axis=0) == 0):.2f}",
    )
    print(f"y fractional overhead {np.mean(~mask):.2f}")
    X = jnp.array(X)
    y = jnp.array(y)
    return X, y, sum_matrix, mask


X_train, y_train = generate(rng, 100)
X_train, y_train, sum_train, mask_train = preprocess(X_train, y_train, 5_000, 100)

X_test, y_test = generate(rng, 100)
X_test, y_test, sum_test, mask_test = preprocess(
    X_test, y_test, sum(len(x) for x in X_test), len(y_test)
)


class MLP(nn.Module):
    nodes: Collection[int]
    nonlin: Callable
    output: Optional[int] = None

    @nn.compact
    def __call__(self, x):
        for size in self.nodes:
            x = nn.Dense(size)(x)
            x = self.nonlin(x)
        if self.output is not None:
            return nn.Dense(self.output)(x)
        return x


class Model(nn.Module):
    phi_nodes: Collection[int]
    rho_nodes: Collection[int]

    def setup(self):
        self.phi = MLP(self.phi_nodes, nn.relu)
        self.rho = MLP(self.rho_nodes, nn.relu, 1)

    @nn.compact
    def __call__(self, x, sum_matrix):
        x = self.phi(x)
        y = sum_matrix @ x
        y = self.rho(y)
        return y.flatten()


def objective(trial):
    rng_key = jax.random.PRNGKey(0)

    width1 = trial.suggest_categorical("width1", [4, 8, 16, 32, 64, 128, 256, 512])
    depth1 = trial.suggest_int("depth1", 1, 10)
    width2 = trial.suggest_categorical("width2", [4, 8, 16, 32, 64, 128, 256, 512])
    depth2 = trial.suggest_int("depth2", 1, 10)
    lr = trial.suggest_float("lr", 1e-5, 0.1, log=True)

    print(f"{width1=} {depth1=} {width2=} {depth2=}")
    model = Model((width1,) * int(depth1), (width2,) * int(depth2))
    theta = model.init(rng_key, X_train, sum_train)
    # model.tabulate does not work with BCOO
    # print(model.tabulate(rng_key, X, sum_matrix))

    opt = optax.adam(learning_rate=lr)
    opt_state = opt.init(theta)

    @jax.jit
    def loss_fn(theta, X, y, sum_matrix, mask):
        yp = model.apply(theta, X, sum_matrix)
        return jnp.mean(mask * (y - yp) ** 2)

    @jax.jit
    def step(theta, opt_state, X, y, sum_matrix, mask):
        loss, grad = jax.value_and_grad(loss_fn)(theta, X, y, sum_matrix, mask)
        updates, opt_state = opt.update(grad, opt_state)
        theta = optax.apply_updates(theta, updates)
        return loss, theta, opt_state

    best_loss = np.inf
    train_loss = []
    test_loss = []
    for epoch in range(5000):
        loss, theta, opt_state = step(
            theta, opt_state, X_train, y_train, sum_train, mask_train
        )
        train_loss.append(loss)

        loss = loss_fn(theta, X_test, y_test, sum_test, mask_test)
        test_loss.append(loss)

        trial.report(loss, epoch)

        if trial.should_prune():
            raise optuna.TrialPruned

        if test_loss[-1] < best_loss:
            best_loss = test_loss[-1]

        stop = np.is_nan(loss) or (
            epoch >= 200 and not np.min(test_loss[-100:]) < np.min(test_loss[-200:-100])
        )

        if stop or epoch % 50 == 0:
            print(
                f"epoch = {epoch:5} "
                f"loss(train) = {train_loss[-1]:6.3f} "
                f"loss(test) = {test_loss[-1]:6.3f}"
            )
        if stop:
            break

    return best_loss


study = optuna.create_study(
    storage="sqlite:///db.sqlite3",  # Specify the storage URL here.
    study_name="deep-set",
)
study.optimize(objective, n_trials=100)
print(f"Best value: {study.best_value} (params: {study.best_params})")
