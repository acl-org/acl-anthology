#
# bibutils converters MAKEFILE
#

CFLAGS     = -I ../lib $(CFLAGSIN)

TOMODS     = args.o bibprog.o tomods.o ../lib/modsout.o

BIBTEXIN   = bib2xml.o ../lib/bibtexin.o ../lib/bibtextypes.o
BIBLATEXIN = biblatex2xml.o ../lib/biblatexin.o ../lib/bltypes.o
COPACIN    = copac2xml.o ../lib/copacin.o ../lib/copactypes.o
EBIIN      = ebi2xml.o ../lib/ebiin.o
ENDIN      = end2xml.o ../lib/endin.o ../lib/endtypes.o
ENDXIN     = endx2xml.o ../lib/endxmlin.o ../lib/endin.o ../lib/endtypes.o
ISIIN      = isi2xml.o ../lib/isiin.o ../lib/isitypes.o
MEDIN      = med2xml.o ../lib/medin.o
MODSCLEAN  = modsclean.o ../lib/modsin.o
RISIN      = ris2xml.o ../lib/risin.o ../lib/ristypes.o
WORDIN     = wordbib2xml.o ../lib/wordin.o

FROMMODS   = bibprog.o args.o ../lib/modsin.o

ADSOUT     = xml2ads.o ../lib/adsout.o
BIBTEXOUT  = xml2bib.o ../lib/bibtexout.o
ENDOUT     = xml2end.o ../lib/endout.o
ISIOUT     = xml2isi.o ../lib/isiout.o
RISOUT     = xml2ris.o ../lib/risout.o
WORDOUT    = xml2wordbib.o ../lib/wordout.o

PROGS      = $(PROGSIN)

all: $(PROGS)

args.o : args.c
	$(CC) $(CFLAGS) -DCURR_VERSION="\"$(VERSION)\"" -DCURR_DATE="\"$(DATE)\"" -c -o $@ $^

bib2xml : $(TOMODS) $(BIBTEXIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

biblatex2xml : $(TOMODS) $(BIBLATEXIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

copac2xml : $(TOMODS) $(COPACIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

ebi2xml : $(TOMODS) $(EBIIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

end2xml : $(TOMODS) $(ENDIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

endx2xml : $(TOMODS) $(ENDXIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

isi2xml : $(TOMODS) $(ISIIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

med2xml : $(TOMODS) $(MEDIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

ris2xml : $(TOMODS) $(RISIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

wordbib2xml : $(TOMODS) $(WORDIN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

xml2ads : $(FROMMODS) $(ADSOUT) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

xml2bib : $(FROMMODS) $(BIBTEXOUT) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

xml2end : $(FROMMODS) $(ENDOUT) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

xml2isi : $(FROMMODS) $(ISIOUT) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

xml2ris : $(FROMMODS) $(RISOUT) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

xml2wordbib : $(FROMMODS) $(WORDOUT) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

modsclean : $(TOMODS) $(MODSCLEAN) ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

test:

install:
	mkdir -p $(INSTALLDIR)
	@for p in $(PROGS); \
                do ( cp $$p$(EXEEXT) $(INSTALLDIR)/ ); \
        done

clean:
	rm -f *.o core 

realclean:
	rm -f *.o core
	@for p in $(PROGS); \
                do ( rm -f $$p$(EXEEXT) ); \
        done
