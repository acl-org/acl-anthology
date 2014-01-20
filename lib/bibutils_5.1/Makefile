CC            = cc
EXEEXT        = 
LIBTARGET     = libbibutils.a
LIBEXT        = .a
CFLAGS        = -D uint=\"unsigned int\" -Wall
CLIBFLAGS     = -D uint=\"unsigned int\" -Wall
RANLIB        = ranlib -s
POSTFIX       = _osx_x86_64
INSTALLDIR    = /usr/local/bin
LIBINSTALLDIR = /usr/local/lib

MAJORVERSION  = 5
MINORVERSION  = 1
VERSION       = $(MAJORVERSION).$(MINORVERSION)
DATE          = 2013-09-03

PROGRAMS      = bib2xml \
                biblatex2xml \
                copac2xml \
                ebi2xml \
                end2xml \
                endx2xml \
                isi2xml \
                med2xml \
                ris2xml \
                wordbib2xml \
                xml2ads \
                xml2bib \
                xml2end \
                xml2isi \
                xml2ris \
                xml2wordbib \
                modsclean

all : FORCE
	$(MAKE) -C lib -k \
                CC=$(CC) \
                CFLAGSIN="$(CLIBFLAGS) $(DISTRO_CFLAGS)"\
                LIBTARGETIN=$(LIBTARGET) \
                MAJORVERSION=$(MAJORVERSION) \
                MINORVERSION=$(MINORVERSION) \
                RANLIB=$(RANLIB)
	$(MAKE) -C bin -k \
                CC=$(CC) \
                CFLAGSIN="$(CFLAGS) $(DISTRO_CFLAGS)"\
                EXEEXT=$(EXEEXT) \
                VERSION="$(VERSION)" \
                DATE="$(DATE)" \
                PROGSIN="$(PROGRAMS)"

clean: FORCE
	$(MAKE) -C lib clean
	$(MAKE) -C bin clean
	$(MAKE) -C test clean

realclean: FORCE
	$(MAKE) -C lib realclean
	$(MAKE) -C bin PROGSIN="$(PROGRAMS)" realclean
	$(MAKE) -C test realclean
	rm -rf update lib/bibutils.pc

test: all FORCE
	$(MAKE) -C lib
	$(MAKE) -C bin test
	$(MAKE) -C test \
                CFLAGSIN="$(CFLAGS) $(DISTRO_CFLAGS)"\
                test

install: all FORCE
	$(MAKE) -C lib \
                LIBTARGETIN=$(LIBTARGET) \
                MAJORVERSION=$(MAJORVERSION) \
                MINORVERSION=$(MINORVERSION) \
                LIBINSTALLDIR=$(LIBINSTALLDIR) \
                install
	$(MAKE) -C bin \
                EXEEXT=$(EXEEXT) \
                PROGSIN="$(PROGRAMS)" \
                INSTALLDIR=$(INSTALLDIR) \
                install
	sed 's/VERSION/${VERSION}/g' packageconfig_start > lib/bibutils.pc

package: all FORCE
	sh -f maketgz.sh $(VERSION) $(POSTFIX) $(LIBTARGET) $(EXEEXT)

deb: all FORCE
	sh -f makedeb.sh $(VERSION) $(POSTFIX)

FORCE:
