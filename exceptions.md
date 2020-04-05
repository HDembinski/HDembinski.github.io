# On C++ exceptions

Here is a collection of advice on using exceptions in high-performance libraries. There has been a lot of discussion in the Boost community about exceptions lately, since [some people want to improve error reporting in C++](http://open-std.org/JTC1/SC22/WG21/docs/papers/2018/p0709r0.pdf), which led to the development of [Boost.Outcome](https://www.boost.org/doc/libs/1_72_0/libs/outcome/doc/html/index.html) and similar libraries.

Further reading:
- https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/boost-exception.html
- https://stackoverflow.com/questions/13835817/are-exceptions-in-c-really-slow
- https://foonathan.net/2017/12/exceptions-vs-expected

# Cost of using exceptions

- Run time:
  - Exceptions have **zero run-time cost** if they do not trigger, but reduce opportunities for optimisation (read on for details)
  - Exceptions that trigger have large costs of O(1000) CPU cycles
- Compile time: small cost
- Code size: small cost in code size

Exceptions were designed to have zero runtime cost when they are not triggered, that is less than an if-branch, but cost O(1000) CPU cycles when they are triggered.

Because of these trade-offs, exceptions should not replace normal control flow with if-else. Exceptions are for exceptional events only, faults that occur rarely and from which the program cannot recover. A good example is wrong user input and unexpected I/O errors.

Google turns off exceptions in all their builds (`-fno-exceptions` in gcc and clang) -- why? Exceptions reduce opportunities for the optimiser to make the code significantly faster, and Google cares about performance very much. The optimiser is allowed to reorder and transform code if it can be proven that this does not change the outcome. Effectively, code that potentially throws exceptions acts like a reorder-barrier. When the exception triggers, the stack has to be identical in the optimised program, which means that the computation of variables on the stack cannot be moved before or after the code that throws.

This has a noticeable effect even in high-performance libraries that use exceptions correctly and use `noexcept` heavily (see next section). In Boost.Histogram, the benchmarks run 10-15 % faster when I deactivate exceptions with `-fno-exceptions`.

# Why and how you should use `noexcept`

The `noexcept` keyword marks a function or method as non-throwing: under no circumstances is it throwing any exception. This is great for the optimiser as it restores the missing opportunities to reorder code.

The compiler trusts this declaration blindly. As of this writing, there is no error or warning if code that was declared `noexcept` throws an exception anyway. If that happens, the program simply aborts. The developer must be careful when using `noexcept`, but it can be very useful when wrapping third-party code that throws exceptions. If all conditions can be anticipated and removed under which the third-party code throws, the wrapped code can be declared `noexcept`.

# When to use assert and when throw an exception

It may be tempting use an `assert` instead of an exception, because the optimiser is troubled by an `assert`. No, don't do that. An `assert` is only checked when the code is compiled in debug mode. Exceptions are always present, also in production code. Therefore, `assert` should never replace exceptions, in particular in code that check or validates user input. Use exceptions for that.

In other words, users should never see a failing `assert`. Anything that can go wrong due to external circumstances outside of the control of the program should trigger an exception. An `assert` is an executable part of the interface documentation: it tells a developer of the code that this code excepts certain inputs and cannot run correctly otherwise.

Rule-of-thumb for using either `assert` or throwing an exception:
- In private interfaces and private implementation code, where you have full control over the input, use `assert` to check the consistency of your program logic
- In user-facing interfaces, use exceptions

Example: Let us say some code requires some external number to be greater than 10. The user-facing layer should then check whether the number is greater than 10 and throw an exception otherwise. The deeper implementation layers should `assert` on the same condition. Under normal circumstances the `assert` will never be violated, but it is there in case you refactor the code and forget to throw the exception in the new user-facing layer.

# How to use exceptions correctly

## Throw, catch, and re-throw exceptions in different software layers

Good modular software is programmed in layers. Exceptions often occur in the the lowest implementation layer. Usually the lowest layer cannot fully report the cause and context of the exception, because the information is not available in that layer.

Here is an example from the documentation of Boost.Exception:
```
void
read_file( FILE * f )
    {
    ....
    const size_t nr = fread(buf, 1, count, f);
    if( ferror(f) )
        throw file_read_error();
    ....
    }
```
If the file cannot be read, `read_file` throws an exception. Users probably want to know which file could not be read, but this layer does not know the file name. It only got a `FILE` pointer.

Changing `read_file` so that it accepts the filename is breaking modularisation. The author of `read_file` cannot and should not need to know in which context this function is used.

A better design is to catch the exception in the layer where the context information like the filename is available, and then add that information to the exception and re-throw it. Implementation-wise, there are some options on how to achieve this. The recommended way is to use [Boost.Exception, as described here](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/motivation.html).

## Keep the actual throwing code out of the hot code path

Throwing an exception in an otherwise small function may prevent the optimiser from inlining this function, because of the additional code generated by the throwing path. However, inlining the throwing code makes no sense, since the throw should never trigger on the hot path anyway.

One can help the optimiser in these situations by wrapping the throw in a small function, e.g. `throw_exception(std::exception const& e)` and mark it with a suitable compiler-specific attribute so that it is never inlined. Such a function is provided by [Boost.Exception](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/throw_exception.html).

## Support compilation with exceptions disabled

If your code throws exceptions at all, it will not compile when exceptions are turned off (the flag `-fno-exceptions` turns off exceptions completely in gcc and clang). As a library developer, you also want your code to compile when exceptions are turned off, since this makes your library useful for more people. At the very least, it helps you to see how much extra performance you loose by using exceptions and whether you need to do something about it (the difference can be reduced by keeping exceptions out of hot code paths).

Again, [Boost.Exception](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/BOOST_THROW_EXCEPTION.html) has a beautiful solution ready: if you consistently use the macro `BOOST_THROW_EXCEPTION` or the function `boost::throw_exception` instead of naked throws (which also has performance benefits as previously mentioned), your code will compile with exceptions disabled. The library will detect this and call a user-defined implementation of `void throw_exception( std::exception const& e , boost::source_location const& l)` for your program in this case, which must abort or exit the program, but can do some custom error logging before.

Boost.Histogram uses Boost.Exception everywhere. This allows me to benchmark it with and without exceptions enabled (and hence I know about the 10-15 % difference in performance). The implementation of `void throw_exception( std::exception const& e, boost::source_location const& l)` in the tests and benchmarks reports about the exception and then aborts the program.
```
void throw_exception(std::exception const& e, boost::source_location const& l) {
  std::cerr << l.file_name() << ":" << l.line() << ":" << l.column() << ": exception in '"
            << l.function_name() << " \"" << e.what() << "\"" << std::endl;
  std::abort();
}
```
