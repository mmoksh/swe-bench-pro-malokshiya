# Missing Compiler Detection
A user reports that Dev-C++ fails to detect an installed GCC/MinGW compiler.

## Bug Report
### Environment
* Dev-C++ 5.11
* Windows
* MinGW installed
* GCC executable present and functional
* Dev-C++ does not detect the compiler

### User Actions Already Attempted
* Reinstalled Dev-C++
* Reinstalled MinGW
* Verified GCC is installed
* Restarted the system
The issue persists.

## Expected Behavior
When Dev-C++ starts, it should automatically discover supported GCC-based toolchains available on the system and configure a usable compiler profile.

Examples include:
* MinGW installed in standard locations
* MinGW installed in custom locations
* GCC available through the PATH environment variable
* Existing compiler configurations from previous installations

## Actual Behavior
* The compiler's directory IS present in the system PATH environment variable. Manually running gcc --version from a Windows command prompt works. However, Dev-C++ reports that no compiler is available even though a valid GCC installation exists.
* Dev-C++ detects compilers only on fresh Windows installations with short PATH variables.

## Requirements
1. Investigate how Dev-C++ discovers and registers compilers, and how the PATH environment variable is read/assembled when UseOriginal is not set.
2. Identify all compiler detection paths currently supported.
3. Determine why valid MinGW/GCC installations are not detected.
4. Implement a robust fix.
5. The fix must not break existing Dev-C++ compiler profiles or previously supported detection workflows.
6. The fix must not require any user intervention or configuration changes.
