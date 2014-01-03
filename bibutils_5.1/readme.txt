
                              COMPILING BIBUTILS.

------------------------------------------------------------------------
STEP 1.  Configure the makefile by running the configure script.

The configure script attempts to auto-identify your operating system
and does a reasonable job for a number of platforms (including x86 Linux,
versions of MacOSX, some BSDs, Sun Solaris, and SGI IRIX).  It's not a 
full-fledged configure script via the autoconf system, but is more than 
sufficient for Bibutils.

Unlike a lot of programs, Bibutils is written in very vanilla ANSI C
with no external dependencies (other than the core C libraries themselves),
so the biggest difference between platforms is generally how they
handle library generation.  If your platform is not recognized, please
e-mail me the output of 'uname -a' and I'll work on adding it.

To configure the makefile, simply run:

% configure

or alternatively

% sh -f configure

The output should look something like:

'
'Bibutils Configuration
'----------------------
'
'Operating system:               Linux_x86_64
'Library and binary type:        static
'Binary installation directory:  /usr/local/bin
'Library installation directory: /usr/local/lib
'
' - If auto-identification of operating system failed, e-mail cdputnam@ucsd.edu
'   with the output of the command: uname -a
'
' - Use --static or --dynamic to specify library and binary type;
'   the --static option is the default
'
' - Set binary installation directory with:  --install-dir DIR
'
' - Set library installation directory with: --install-lib DIR
'
'
'To compile,                  type: make
'To install,                  type: make install
'To make tgz package,         type: make package
'To make deb package,         type: make deb
'
'To clean up temporary files, type: make clean
'To clean up all files,       type: make realclean


By default, the configure script generates Makefiles to generate statically
linked binaries.  These binaries are the largest, but require no management of
dynamic libraries, which can be subtle for users not used to installing
them and ensuring that the operating system knows where they are.
Dynamically linked binaries take up substantially less disk space, but require
real machine and distribution specific knowledge for handling the dynamic
library installation and usage.  All of the distributed binaries are statically
linked for obvious reasons.

-----------------------------------------------------------------------
STEP 2.  Make the package with make

% make

----------------------------------------------------------------------
STEP 3.  Install the package

% make install

Note that 'make install' won't install the libraries with statically-
linked binaries but will (naturally) with dynamically-linked binaries.

