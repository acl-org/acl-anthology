#
# bibutils unit tests MAKEFILE
#

CFLAGS     = -I ../lib $(CFLAGSIN)
PROGS      = doi_test \
             entities_test \
             list_test \
             newstr_test \
             utf8_test

all: $(PROGS)

entities_test : entities_test.o ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

utf8_test : utf8_test.o ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

doi_test : doi_test.o ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

newstr_test : newstr_test.o ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

list_test : list_test.o ../lib/libbibcore.a
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@

test: $(PROGS) FORCE
	./newstr_test
	./list_test
	./entities_test
	./doi_test
	./utf8_test

clean:
	rm -f *.o core 

realclean:
	rm -f *.o core $(PROGS)
	@for p in $(PROGS); \
               do ( rm -f $$p$(EXEEXT) ); \
        done

FORCE:
