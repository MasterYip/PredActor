# Unitree joystick header provenance

- Imported unchanged from `unitreerobotics/unitree_sdk2`
- Source commit: `f29ee9f234851e9e79f75102c0f9e83008d8fdd1`
- Source path: `include/unitree/dds_wrapper/common/unitree_joystick.hpp`
- SHA-256: `f8213333a45b92e8df6e83d481ccca48c33eeb307326f6c75c3912ac1b6ed730`
- License: BSD 3-Clause, copied as `UNITREE_SDK2_LICENSE`

This package-owned copy supports G1 images whose flat SDK2 installation omits
the upstream helper header. It preserves Unitree's original joystick decoding.

The same source commit supplies the package-owned G1 receive-only IDL closure:

- `unitree/idl/hg/LowState_.hpp`: `e01be29667100a6f2cd829b3ea8a90f846271b20a0cde96331ceecfb4d46e042`
- `unitree/idl/hg/IMUState_.hpp`: `0b078db5401a35c2421190adb98c0a7e94472ee798b20aa4d1a345513dc88b1b`
- `unitree/idl/hg/MotorState_.hpp`: `9a461ce785c1d56e95c284065178935288d04fd3261090983ab0fd0c2c6d8f0d`

No G1 command IDL is bundled; command publishing remains unavailable.
