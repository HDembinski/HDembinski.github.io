#include <pybind11/pybind11.h>
#include <numpy/random/bitgen.h>
#include <iostream>

namespace py = pybind11;
using namespace py::literals;

extern "C" {
    // implemented in fortran
    void setbitg_(void*);
    void numpyrng_(double*);

    // called from Fortran
    void next_(double* value, void** bitgen)
    {
        auto bg = static_cast<bitgen_t*>(*bitgen);
        *value = bg->next_double(bg->state);
    }
}

// pass random state created by Numpy to Fortran
void init_fortran(py::object rng) {
    py::object pybitgen = rng.attr("bit_generator");
    py::capsule cap = pybitgen.attr("capsule");
    bitgen* bg = static_cast<bitgen*>(cap);
    assert(bg);
    setbitg_(reinterpret_cast<void*>(bg));
}

double call_fortran() {
    double val;
    numpyrng_(&val);
    return val;
}

PYBIND11_MODULE(rangen, m) {
    m.def("init_fortran", &init_fortran, "rng"_a);
    m.def("call_fortran", &call_fortran);
}
