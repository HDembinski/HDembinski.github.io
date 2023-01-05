program hello
    USE, INTRINSIC :: ISO_C_BINDING
    implicit none

    real(c_double) :: val = 0

    ! this initializes the PRNG on the C side and passes
    ! the pointer to the fortran side, where it is stored
    ! in the common block
    call init()

    call rng(val)

    print *, "Here is a random number for you", val
end program


subroutine set_rstate(void_ptr) BIND(C,name='set_rstate')
USE, INTRINSIC :: ISO_C_BINDING
implicit none
    type(c_ptr), intent(in) :: void_ptr
    common rstate
    type(c_ptr) :: rstate
    rstate = void_ptr
end subroutine


subroutine rng(val)
USE, INTRINSIC :: ISO_C_BINDING
    real (c_double) :: val
    common rstate
    type(c_ptr) :: rstate
    call next(val, rstate)
end subroutine
