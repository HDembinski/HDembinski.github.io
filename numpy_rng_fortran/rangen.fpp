      SUBROUTINE SETBITG( PTR )
      USE, INTRINSIC :: ISO_C_BINDING
      IMPLICIT NONE

      COMMON BITGEN
      TYPE(C_PTR) :: BITGEN
      TYPE(C_PTR), VALUE :: PTR

      BITGEN = PTR

      RETURN
      END


      SUBROUTINE NUMPYRNG( RVAL )
      USE, INTRINSIC :: ISO_C_BINDING
      IMPLICIT NONE

      DOUBLE PRECISION RVAL
      COMMON BITGEN
      TYPE(C_PTR) :: BITGEN

      CALL NEXT(RVAL, BITGEN)

      RETURN
      END

C=======================================================================

      SUBROUTINE RM48( RVEC,LENV )

C-----------------------------------------------------------------------
C  R(ANDO)M (NUMBER GENERATOR FOR EVAPORATION MODULE/DPMJET)
C
C  THIS SUBROUTINE IS CALLED FROM ROUTINES OF EVAPORATION MODULE.
C  ARGUMENTS:
C   RVEC   = DOUBL.PREC. VECTOR FIELD TO BE FILLED WITH RANDOM NUMBERS
C   LENV   = LENGTH OF VECTOR (# OF RANDNUMBERS TO BE GENERATED)
C-----------------------------------------------------------------------

      IMPLICIT NONE

      DOUBLE PRECISION RVEC(*), RVAL
      INTEGER          LENV, I
      SAVE

      DO 100 I = 1, LENV
        CALL NUMPYRNG(RVAL)
        RVEC(I) = RVAL
 100  CONTINUE

      RETURN
      END


C=======================================================================

      DOUBLE PRECISION FUNCTION SIMRND()

C-----------------------------------------------------------------------
C  (SIM)PLIFIED RANDOM NUMBER GENERATOR CALL TO NUMPYRNG
C-----------------------------------------------------------------------

      CALL NUMPYRNG(SIMRND)

      RETURN
      END

C=======================================================================

C====================       WRAPPERS     ===============================
#ifdef SIBYLL_21
#define S_RNDM_RESULT REAL
#else
#define S_RNDM_RESULT DOUBLE PRECISION
#endif

      S_RNDM_RESULT FUNCTION S_RNDM()

C-----------------------------------------------------------------------
C  S(IBYLL) R(A)ND(O)M (GENERATOR)
C-----------------------------------------------------------------------

      IMPLICIT NONE

      DOUBLE PRECISION SIMRND

#ifdef SIBYLL_21
555   S_RNDM = real(SIMRND())
      IF ((S_RNDM.LE.0E0).OR.(S_RNDM.GE.1E0)) GOTO 555     
#else
      S_RNDM = SIMRND()
#endif

      RETURN
      END


      DOUBLE PRECISION FUNCTION PYR()

C-----------------------------------------------------------------------
C  PY(THIA) R(ANDOM GENERATOR)
C-----------------------------------------------------------------------

      IMPLICIT NONE

      CALL NUMPYRNG(PYR)

      RETURN
      END

      DOUBLE PRECISION FUNCTION RNDM()

C-----------------------------------------------------------------------
C  R(A)ND(O)M (GENERATOR FOR DPMJET)
C-----------------------------------------------------------------------

      IMPLICIT NONE

      CALL NUMPYRNG(RNDM)

      RETURN
      END

      DOUBLE PRECISION FUNCTION PSRAN()

C-----------------------------------------------------------------------
C  RAN(DOM GENERATOR FOR QGSJET)
C-----------------------------------------------------------------------

      IMPLICIT NONE

      CALL NUMPYRNG(PSRAN)

      RETURN
      END

      DOUBLE PRECISION FUNCTION RANF()

C-----------------------------------------------------------------------
C  RAN(DOM GENERATOR FOR URQMD
C-----------------------------------------------------------------------

      IMPLICIT NONE

      CALL NUMPYRNG(RANF)

      RETURN
      END


      DOUBLE PRECISION FUNCTION RLU()

C-----------------------------------------------------------------------
C  RLU  RANDOM GENERATOR FOR JETSET
C-----------------------------------------------------------------------

      IMPLICIT NONE

      CALL NUMPYRNG(RLU)

      RETURN
      END

      DOUBLE PRECISION FUNCTION DT_RNDM(VDUMMY)

C-----------------------------------------------------------------------
C  THIS FUNCTON IS CALLED FROM DPM_JET306 ROUTINES.
C-----------------------------------------------------------------------

      IMPLICIT NONE

      DOUBLE PRECISION VDUMMY

      CALL NUMPYRNG(DT_RNDM)

      RETURN
      END
