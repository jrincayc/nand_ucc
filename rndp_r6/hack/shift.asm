.equ GXP, 1990
.equ GYP, 65522
.equ GXR, 1494
.equ GYR, 290
.macro SETXP v k
    .byte 7,\v,lo((\k+GXP)),hi((\k+GXP))
.endm
.macro SETYP v k
    .byte 7,\v,lo((\k+GYP)),hi((\k+GYP))
.endm
.macro SETXR v k
    .byte 7,\v,lo((\k+GXR)),hi((\k+GXR))
.endm
.macro SETYR v k
    .byte 7,\v,lo((\k+GYR)),hi((\k+GYR))
.endm
