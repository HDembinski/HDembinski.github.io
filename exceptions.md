# On C++ exceptions

Here is a collection of advice on using exceptions in high-performance libraries. There has been a lot of discussion in the Boost community about exceptions lately, since [some people want to](http://open-std.org/JTC1/SC22/WG21/docs/papers/2018/p0709r0.pdf) [improve error reporting in C++](http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1095r0.pdf), which led to the development of [Boost.Outcome](https://www.boost.org/doc/libs/1_72_0/libs/outcome/doc/html/index.html) and similar libraries. Here we deal with classic C++ exceptions.

Further reading:
- https://www.boost.org/community/error_handling.html
- [Scott Meyers, Effective Modern C++, O'Reilly](http://shop.oreilly.com/product/0636920033707.do)
- https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines
- https://www.boost.org/community/exception_safety.html
- https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/boost-exception.html
- http://open-std.org/JTC1/SC22/WG21/docs/papers/2018/p0709r0.pdf
- http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1095r0.pdf
- https://stackoverflow.com/questions/13835817/are-exceptions-in-c-really-slow
- https://stackoverflow.com/questions/26079903/noexcept-stack-unwinding-and-performance
- https://en.cppreference.com/w/cpp/language/noexcept_spec

I thank users on the cpplang boost channel for feedback and additional links.

## Why use exceptions and not an alternative?

Exceptions are the official language feature of C++ for reporting errors. There are two cases in C++ where other error reporting systems based on return values do not work: in constructors (which do not return) and in operators (which must use the return value for something else). There are workarounds for these cases, but they lead to less idiomatic C++. Of course, [there are also reasons](https://google.github.io/styleguide/cppguide.html#Exceptions) [to avoid exceptions](https://www.boost.org/doc/libs/1_72_0/libs/outcome/doc/html/motivation/exceptions.html). [Herb Sutter gives a comprehensive overview of the various pros and cons of exceptions and their alternatives](http://open-std.org/JTC1/SC22/WG21/docs/papers/2018/p0709r0.pdf).

## Cost of using exceptions

- Run time:
  - Exceptions have **zero run-time cost** if they do not trigger, but reduce optimisation opportunities (read on for details)
  - Exceptions that trigger have [a large cost (thousands of CPU cycles)](https://docs.google.com/presentation/d/1fSkpD51FKmy8VEO9P86jWN6tOEaBmzHOXo14zLRkFKE/edit#slide=id.g40eacd9a43_0_102)
- Compile time: small cost
- Code size increases by [about +15 % to +40 %](http://open-std.org/JTC1/SC22/WG21/docs/papers/2018/p0709r0.pdf)

Exceptions in C++ were designed to have zero run time cost when they do not trigger. Zero cost is even less cost than an if-else-branch. In theory, this makes C++ exceptions more performant than the C style alternative of returning an error code on the happy path (but read on). C++ exceptions cost a lot of cycles when they trigger. Therefore, exceptions should never be used for normal control flow, where both alternatives happen regularly. Exceptions are for exceptional events only, faults that occur rarely during the run of a program. A good example is wrong user input and unexpected I/O errors.

So exceptions seem pretty great, but Google turns off exceptions in their builds (`-fno-exceptions` in gcc and clang) -- why? [Apart from stylistic issues](https://google.github.io/styleguide/cppguide.html#Exceptions), exceptions reduce opportunities for the optimiser to make the code faster. The optimiser is allowed to transform code if it can prove that this does not change the visible outcome. A potentially throwing expression can prevent fusing instructions before and after the expression. When the exception triggers, the instructions after the exception are not executed. If this has observable side effects, the [optimiser cannot fuse the instructions to increase performance](https://godbolt.org/z/9YAdaz).

All in all, this has a noticeable effect even in carefully written libraries that use exceptions. In Boost.Histogram, benchmarks run 10-15 % faster when I deactivate exceptions with `-fno-exceptions`, even though no exceptions are thrown in these benchmarks.

## How to use `noexcept`

The `noexcept` specifier marks a function or method as not throwing any exception ever. This is great for the optimiser.

The compiler trusts this declaration. You won't get a compile-time error if code that was declared `noexcept` throws an exception anyway. [If that happens at run-time, the program simply terminates](https://en.cppreference.com/w/cpp/error/terminate). Compilers may emit a warning about this, but only in obvious cases[<sup>1</sup>](#1). The developer must make sure to not lie to the compiler when declaring something as `noexcept`.

There are legitimate reasons to declare a function `noexcept` which has throwing internal code (which may be third-party code). If all conditions can be anticipated and explicitly handled under which the internal code could throw, the surrounding code can be declared `noexcept` since no throw will actually occur. While this should be a performance gain in theory, [in reality it depend on the compiler support for `noexcept`](https://github.com/N-Dekker/noexcept_benchmark).

It is not necessary to mark every non-throwing function or method as `noexcept`, [the compiler is able to detect simple cases](https://en.cppreference.com/w/cpp/language/noexcept).

<a class="anchor" id="1">Note 1: At the time of this writing, neither gcc or clang [warn if the throw is nested in another function](https://godbolt.org/z/F_lBdZ).</a>

## Best practices when using C++ exceptions

### assert or throw an exception?

It may be tempting use an `assert` instead of an exception, because the optimiser is not troubled by an `assert`, but don't do that. An `assert` is usually only checked when the code is compiled in debug mode[<sup>2</sup>](#2), while exceptions work also in production code. Therefore, an `assert` cannot be used in place of an exception, in particular in code that checks or validates user input.

Rule-of-thumb for using either `assert` or throwing an exception:
- In private interfaces and private implementation code, where you have full control over the input, use `assert` to check the consistency of your program logic
- In user-facing interfaces, use exceptions

In other words, users should never see a failing `assert`. Anything that can go wrong due to external circumstances outside of the control of the program should trigger an exception. An `assert` is an executable part of the interface documentation: it reminds a developer that this code expects certain inputs and cannot run correctly when these are violated.

Example: Let us say some code requires some user-defined number to be greater than 10. The user-facing layer should check whether the number is greater than 10 and otherwise throw an exception. The deeper implementation layers should `assert` on the same condition. This is not redundant, since the `assert` documents what the implementation layer expects. If the program is not altered, the `assert` will never be violated, but it is there in case someone refactors the code and forgets to protect the implementation layer from invalid external input.

<a class="anchor" id="2">Note 2: To be more precise, the `assert` macro from `<cassert>` expands to nothing [when `-DNDEBUG` is set](https://en.cppreference.com/w/c/error/assert), which is usually set in a release build (for example, this is the `cmake` default).</a>

### Destructors, move constructors, and move assignment should not throw

If the implementation allows it at all, destructors, move constructors, and move-assignment operators should not throw exceptions. If they are not declared `noexcept` (more details on `noexcept` are given below), [the compiler will try to figure this out](https://en.cppreference.com/w/cpp/language/noexcept).

[Throwing destructors are a really bad idea](https://isocpp.org/wiki/faq/exceptions#dtors-shouldnt-throw), because destructors are called during the stack-unwinding when another exception was thrown. If the exception is allowed to leave the destructor in this situation, the program will terminate immediately[<sup>3</sup>](#3).

Containers like `std::vector` need their elements to have non-throwing move constructors and move-assignment to make efficient use of them. Containers typically want to guarantee that they are in a valid state at all times. For example, `std::vector::push_back` grants the *strong exception guarantee*: if an exception is thrown while the method runs, the vector is guaranteed to remain in its original state. This guarantee cannot be given if moves can throw. For moves to be efficient, the original value in the container has to be destroyed before the new value is moved into its memory block. If the move operation throws, the original value cannot be restored. Since correctness is more important than performance, `std::vector::push_back` [tries to copy values instead of moving them when moves can throw](https://en.cppreference.com/w/cpp/container/vector/push_back).

The existance of throwing moves caused considerable head ache for developers of type-safe union types, like [`std::variant`](https://en.cppreference.com/w/cpp/utility/variant) and [`boost::variant2`](https://www.boost.org/doc/libs/1_72_0/libs/variant2/doc/html/variant2.html). While `std::variant` [gives up on the strong exception guarantee](https://en.cppreference.com/w/cpp/utility/variant/valueless_by_exception) in this case, [`boost::variant2` adheres to it](https://www.boost.org/doc/libs/1_72_0/libs/variant2/doc/html/variant2.html#design_strong_exception_safety) at the cost of doubling the size of the variant if any type in the variant set has throwing moves.

<a class="anchor" id="3">Note 3: [It is possible to detect the exception in flight](https://stackoverflow.com/questions/1187692/how-to-detect-when-an-exception-is-in-flight) and react, but that is a really unappealing solution.</a>

### Throwing, catching, and re-throw exceptions in different software layers is good

Good software is programmed in layers of abstraction. Exceptions often occur in the lowest implementation layer. Sometimes the lowest layer cannot fully report the context of the exception, because the information is not available in that layer.

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

### Improve inlining opportunities for code that throws

Throwing an exception in an otherwise small function or method may prevent the optimiser from inlining it. The `throw` path generates additional instructions which increases the size of the function body, even if it is rarely triggered. The inliner tries to balance the overall increase in code size from inlining against possible performance benefits and may refuse to inline due to the presence of the throw instructions.

One can help the optimiser in these situations by wrapping the `throw` in a small function, e.g. `throw_exception(std::exception const& e)` and mark it with a compiler-specific attribute so that it is never inlined. Such a function is readily provided by [Boost.Exception](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/throw_exception.html). The surrounding code is now much leaner since it contains only an instruction to call a function pointer, and the optimiser will find more opportunities to inline it.

### Support compilation with exceptions disabled

If your code throws exceptions at all, it will not compile when exceptions are turned off in the compiler (for example, with the flag `-fno-exceptions` in gcc and clang). As a library developer, you should be interested in supporting compilation without exceptions, [since this makes your library useful for more people](https://stackoverflow.com/questions/691168/how-much-footprint-does-c-exception-handling-add). At the very least, it helps you to see whether you currently loose performance by using exceptions and whether something has to be done about it (often implementations can be manually optimised to keep the cost small).

Again, [Boost.Exception](https://www.boost.org/doc/libs/1_72_0/libs/exception/doc/BOOST_THROW_EXCEPTION.html) has a solution ready: if you consistently use the macro `BOOST_THROW_EXCEPTION` or the function `boost::throw_exception` instead of a naked `throw` (which also has the performance benefits previously mentioned), your code will compile even when exceptions are disabled. The library will detect this and call a user-defined implementation of `void throw_exception( std::exception const& e , boost::source_location const& l)` instead, which must terminate the program but can run error logging or clean up code before. If the code also catches and rethrows exceptions, the keywords `try` and `catch` need to be conditionally hidden, for example, like this
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
