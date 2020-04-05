# On C++ exceptions

Here is a collection of advice on using exceptions in high-performance libraries. There has been a lot of discussion in the Boost community about exceptions lately, since [some people want to improve error reporting in C++](http://open-std.org/JTC1/SC22/WG21/docs/papers/2018/p0709r0.pdf), which led to the development of [Boost.Outcome](https://www.boost.org/doc/libs/1_72_0/libs/outcome/doc/html/index.html) and similar libraries.

Further reading:
- https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/boost-exception.html
- https://stackoverflow.com/questions/13835817/are-exceptions-in-c-really-slow
- https://foonathan.net/2017/12/exceptions-vs-expected
- https://en.cppreference.com/w/cpp/language/noexcept_spec

# Cost of using exceptions

- Run time:
  - Exceptions have **zero run-time cost** if they do not trigger, but may reduce opportunities for optimisation (read on for details)
  - Exceptions that trigger have large cost (thousands of CPU cycles)
- Compile time: small cost
- Code size: small cost

Exceptions in C++ were designed to have zero run time cost when they do not trigger. Zero cost is even less cost than an if-else-branch. In theory, this makes C++ exceptions more performant than the C style alternative of returning an error code (but read on). C++ exceptions cost a lot of cycles when they trigger. Thereofore, exceptions should never be used for normal control flow, where both alternatives happen regularly. Exceptions are for exceptional events only, faults that occur rarely. A good example is wrong user input and unexpected I/O errors.

So exceptions seem pretty great, but Google turns off exceptions in all their builds (`-fno-exceptions` in gcc and clang) -- why? Exceptions reduce opportunities for the optimiser to make the code faster. The optimiser is allowed to reorder and transform code if it can prove that this does not change the visible outcome. Effectively, code that potentially throws exceptions acts like a barrier for reordering, which is typically the first step before applying more powerful optimisations. When the exception triggers, the current stack has to look identical in the optimised program, which means that the computation of variables on the stack cannot be moved before or after the code that throws.

This has a noticeable effect even in carefully written libraries that use exceptions correctly and use `noexcept` heavily (see next section). In Boost.Histogram, benchmarks run 10-15 % faster when I deactivate exceptions with `-fno-exceptions`.

# Best practices when using C++ exceptions

## assert or throw an exception?

It may be tempting use an `assert` instead of an exception, because the optimiser is not troubled by an `assert`, but no, don't do that. An `assert` is only checked when the code is compiled in debug mode, while exceptions are present even in production code. Therefore, an `assert` should never replace an exception, in particular in code that check or validates user input. Use exceptions for that.

Rule-of-thumb for using either `assert` or throwing an exception:
- In private interfaces and private implementation code, where you have full control over the input, use `assert` to check the consistency of your program logic
- In user-facing interfaces, use exceptions

In other words, users should never see a failing `assert`. Anything that can go wrong due to external circumstances outside of the control of the program should trigger an exception. An `assert` should be seen as an executable part of the interface documentation: it reminds a developer that this code expects certain inputs and cannot run correctly when these are violated.

Example: Let us say some code requires some user-defined number to be greater than 10. The user-facing layer should check whether the number is greater than 10 and otherwise throw an exception. The deeper implementation layers should `assert` on the same condition. This is not redundant, since the `assert` documents what the implementation layer expects. If the program is not altered, the `assert` will never be violated, but it is there in case someone refactors the code and forgets to protect the implementation layer from invalid external input.

## Throwing, catching, and re-throw exceptions in different software layers is good

Good modular software is programmed in layers. Exceptions often occur in the lowest implementation layer. Sometimes the lowest layer cannot fully report the context of the exception, because the information is not available in that layer.

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

A better design is to catch the exception in a higher layer where the context information, like the filename, is available, and then add that information to the exception and re-throw it. [Boost.Exception](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/motivation.html) offers `boost::exception` which derives from `std::exception` and allows one to add arbitrary information to an exception in flight.

## Keep throwing code out of the hot code path

Throwing an exception in an otherwise small function may prevent the optimiser from inlining this function. The throwing path generates additional code which bloats the function body, even if it is rarely triggered. The inliner tries to balance the increase in overall code size from inlining against the possible performance benefits and may make the wrong decision due to the presence of the throw.

One can help the optimiser in these situations by wrapping the `throw` in a small function, e.g. `throw_exception(std::exception const& e)` and mark it with a compiler-specific attribute so that it is never inlined. Such a function is readily provided by [Boost.Exception](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/throw_exception.html). The small function with which we originally started is now much leaner, since it contains only a call of a function pointer, and the inliner will more readily inline it.

## Support compilation with exceptions disabled

If your code throws exceptions at all, it will not compile when exceptions are turned off in the compiler (for example, with the flag `-fno-exceptions` in gcc and clang). As a library developer, you should be interested in supporting compilation without exceptions, [since this makes your library useful for more people](https://stackoverflow.com/questions/691168/how-much-footprint-does-c-exception-handling-add). At the very least, it helps you to see whether you currently loose performance by using exceptions and whether something has to be done about it (often implementations can be manually optimised to keep the cost small).

Again, [Boost.Exception](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/BOOST_THROW_EXCEPTION.html) has a beautiful solution ready: if you consistently use the macro `BOOST_THROW_EXCEPTION` or the function `boost::throw_exception` instead of naked throws (which also has performance benefits as previously mentioned), your code will compile even when exceptions are disabled. The library will detect this and call a user-defined implementation of `void throw_exception( std::exception const& e , boost::source_location const& l)` for your program instead, which must terminate the program but can run error logging or clean up code before. If the code also catches and rethrows exceptions, the keywords `try` and `catch` need to be conditionally hidden, for example, like this
```
#ifdef BOOST_NO_EXCEPTIONS
  potentially_throwing(....);
#else
try {
  potentially_throwing(....);
} catch(....) {
  ....
}
#endif
```

Boost.Histogram uses Boost.Exception everywhere. This allows me to benchmark it with and without exceptions enabled (and thus I know about the 10-15 % difference in performance). The simple implementation of `void throw_exception( std::exception const& e, boost::source_location const& l)` in the tests and benchmarks reports where the exception has occured and then aborts the program.
```
void throw_exception(std::exception const& e, boost::source_location const& l) {
  std::cerr << l.file_name() << ":" << l.line() << ":" << l.column() << ": exception in '"
            << l.function_name() << " \"" << e.what() << "\"" << std::endl;
  std::abort();
}
```

## How to use `noexcept`

The `noexcept` specifier marks a function or method as non-throwing: under no circumstances is it throwing any exception. This is great for the optimiser, it restores the opportunities to reorder code.

The compiler trusts this declaration blindly. You won't get a compile-time error or warning if code that was declared `noexcept` throws an exception anyway. [If that happens, the program simply aborts](https://en.cppreference.com/w/cpp/error/terminate). The developer must make sure to not lie to the compiler when declaring something as `noexcept`. However, there are legitimate reasons to declare a function `noexcept` which has throwing internal code (which may be third-party code). If all conditions can be anticipated and explicitly handled under which the internal code could throw, the surrounding code can be declared `noexcept` since no throw will actually occur.
