#!/usr/bin/env perl
# -*- cperl -*-
=head1 NAME

anthoBibs2xml.pl

=head1 SYNOPSYS

 RCS:$Id$

=head1 DESCRIPTION

=head1 HISTORY

 ORIGIN: created from templateApp.pl version 3.4 by Min-Yen Kan <kanmy@comp.nus.edu.sg>

 RCS:$Log$

=cut

require 5.0;
use Getopt::Std;
use strict 'vars';
# use diagnostics;

### USER customizable section
my $tmpfile .= $0; $tmpfile =~ s/[\.\/]//g;
$tmpfile .= $$ . time;
if ($tmpfile =~ /^([-\@\w.]+)$/) { $tmpfile = $1; }		      # untaint tmpfile variable
$tmpfile = "/tmp/" . $tmpfile;
$0 =~ /([^\/]+)$/; my $progname = $1;
my $outputVersion = "1.0";

my %entities = (
		"“" => "\"",
		"”" => "\"",
		"--" => "&#8211;",
		"\\#" => "#",
		"\\_" => "_",
		"\\&" => "&#38;",

		"``" => "&#x201c;",
		"&ldquo;" => "&#x201c;",
		"''" => "&#x201d;",
		"&rdquo;" => "&#x201d;",
		"&rsquo;" => "'",
		"\\textquotesingle" => "'",
		"\\textendash" => "&#x02013;",
		"\\textemdash" => "&#x02014;",
		"{\\\"a}" => "&#228;",
		"\\\"{a}" => "&#228;",
		"\\\`{a}" => "&#224;",
		"\\r{A}" => "&#197;",
		"\\r{a}" => "&#229;",
		"\\\`{A}" => "&#192;",
		"{\\\`a}" => "&#224;",
		"\\\'{a}" => "&#225;",
		"\\\'a" => "&#225;",
		"{\\\'a}" => "&#225;",
		"\\\'{A}" => "&#193;",
		"{\\\'A}" => "&#193;",
		"\\\={a}" => "&#257;",
		"\\\={A}" => "&#256;",
		"\\v{a}" => "&#x103;",
		"\\v{A}" => "&#x102;",
		"\\u{a}" => "&#x103;",
		"\\u{A}" => "&#x102;",
		"á" => "&#225;",
		"&acirc;" => "&#226;",
		"{\\\^a}" => "&#226;",
		"\\\^{a}" => "&#226;",
		"\\\~{a}" => "&#227;",
		"&aring;" => "&#229;",
		"&aelig;" => "&#230;",
		"{\\\'c}" => "&#263;",
		"{\\\'C}" => "&#262;",
		"\\c{c}" => "&#231;",
		"\\c{C}" => "&#199;",
		"{\\c c}" => "&#231;",
		"\\\'{E}" => "&#201;",
		"{\\\'E}" => "&#201;",
		"\\\'E" => "&#201;",
		"\\\`e" => "&#232;",
		"\\\"e" => "&#235;",
		"\\\`{e}" => "&#232;",
		"{\\\`e}" => "&#232;",
		"\\\'{e}" => "&#233;",
		"\{\\\'e\}" => "&#233;",
		"{\\\'e}" => "&#233;",
		"\\.{e}" => "ė",
		"{\\.e}" => "ė",
		"\\.e" => "ė",
		"\\\'e" => "&#233;",
		"&eacute;" => "&#233;",
		"é" => "&#233;",
		"&ecirc;" => "&#234;",
		"\\v{e}" => "&#x115;",
		"\\v{E}" => "&#x114;",
		"{\\\^e}" => "&#234;",
		"\\\^{e}" => "&#234;",
		"\\\"{e}" => "&#235;",
		"{\\\"e}" => "&#235;",
		"\\u{G}"=> "&#286;",
		"\\u{g}"=> "&#287;",
		"{\\\`i}" => "&#236;",
		"\\\`{i}" => "&#236;",
		"\\\`{\\i}" => "&#236;",
		"&igrave;" => "&#236;",
		"{\\\'i}" => "&#237;",
		"\\\'{i}" => "&#237;",
		"\\\'i" => "&#237;",
		"{\\\'\\\i}" => "&#237;",
		"\\\i{}" => "&#x131;",
		"\\\{i}" => "&#x131;",
		"{\\i}" => "&#x131;",
		"\\'{\\i}" => "&#237;",
		"&iacute;" => "&#237;",
		"í" => "&#237;",
		"{\\\^i}" => "&#238;",
		"\\\^{\\i}" => "&#238;",
		"{\\\^\\i}" => "&#238;",
		"\\\^{i}" => "&#238;",
		"\\\"{\\i}" => "&#239;",
		"\\\"{i}" => "&#239;",
		"{\\\"i}" => "&#239;",
		"{\\\"\\i}" => "&#239;",
		"{\\dh}" => "&#240;",
		"{\\\'I}" => "&#205;",
		"\\\.{I}" => "&#x130;",
		"\\c{l}" => "&#x13c;",
		"{\\c l}" => "&#x13c;",
		"\\c\{L}" => "&#x13b;",
		"&eth;" => "&#240;",
		"&ntilde;" => "&#241;",
		"&nacute;" => "&#x144;",
		"&Nacute;" => "&#x143;",
		"\\\'{n}" => "&#x144;",
		"\\\'{N}" => "&#x143;",
		"ñ" => "&#241;",
		"\\\~{n}" => "&#241;",
		"{\\\~n}" => "&#241;",
		"{\\c n}" => "&#x146;",
		"{\\c N}" => "&#x145;",
		"\\c{n}" => "&#x146;",
		"\\c{N}" => "&#x145;",
		"\\v{n}" => "&#x148;",
		"&ograve;" => "&#242;",
		"\\\'{O}" => "&#x00d3;",
		"\\\'{o}" => "&#243;",
		"{\\\'o}" => "&#243;",
		"\\\^{O}" => "&#212;",
		"\\\^{o}" => "&#244;",
		"\\^{O}" => "&#212;",
		"\\^{o}" => "&#244;",
		"ó" => "&#243;",
		"&ocirc;" => "&#244;",
		"{\\^O}" => "&#212;",
		"{\\^o}" => "&#244;",
		"\\\~{o}" => "&#245;",
		"{\\\~o}" => "&#245;",
		"{\\\~O}" => "&#213;",
		"&otilde;" => "&#245;",
		"{\\O}" => "&#216;",
		"\\\"{O}" => "&#214;",
		"{\\\"O}" => "&#214;",
		"{\\\"o}" => "&#246;",
		"\\\"{o}" => "&#246;",
		"&divide;" => "&#247;",
		"{\\o}" => "&#248;",
		"{\\o}" => "&#248;",
		"&ugrave;" => "&#249;",
		"\\\`{u}" => "&#249;",
		"{\\\`u}" => "&#249;",
		"\\\'{u}" => "&#250;",
		"{\\\'u}" => "&#250;",
		"\\\'{U}" => "&#218;",
		"{\\\'U}" => "&#218;",
		"\\={u}" => "ū",
		"&ucirc;" => "&#251;",
		"{\\\^u}" => "&#251;",
		"\\\^{u}" => "&#251;",
		"\\\"{U}" => "&#220;",
		"{\\\"U}" => "&#220;",
		"\\\"{u}" => "&#252;",
		"{\\\"u}" => "&#252;",
		"ü" => "&#252;",
		
		"&yacute;" => "&#253;",
		"&thorn;" => "&#254;",
		"&yuml;" => "&#255;",
		"&fnof;" => "&#402;",
		"&circ;" => "&#710;",
		"&tilde;" => "&#732;",

		"&rdquo;" => "&#8221;",
		"&ldquo;" => "&#8220;",
		"&rsquo;" => "&#8217;",
		"&lsquo;" => "&#8216;",

		"&abreve;" => "&#x103;",
		"&Abreve;" => "&#x102;",
		"&amacr;" =>  "&#x101;",
		"{\\\= a}" =>  "&#x101;",
		"{\\\= A}" =>  "&#x100;",
		"&Amacr;" =>  "&#x100;",
		"&aogon;" =>  "&#x105;",
		"&Aogon;" =>  "&#x104;",
		"\\\'{c}" => "&#x107;",
		"&Cacute;" => "&#x106;",
		"\\v{c}" => "&#x10D;",
		"\\v{C}" => "&#x10C;",
		"&ccaron;" => "&#x10D;",
		"&Ccaron;" => "&#x10C;",
		"&ccirc;" =>  "&#x109;",
		"&Ccirc;" =>  "&#x108;",
		"&cdot;" =>   "&#x10B;",
		"&Cdot;" =>   "&#x10A;",
		"&dcaron;" => "&#x10F;",
		"&Dcaron;" => "&#x10E;",
		"&dstrok;" => "&#x111;",
		"&Dstrok;" => "&#x110;",
		"&ecaron;" => "&#x11B;",
		"&Ecaron;" => "&#x11A;",
		"&Eacute;" => "&#201;",
		"&edot;" =>   "&#x117;",
		"&Edot;" =>   "&#x116;",
		"&emacr;" =>  "&#x113;",
		"&Emacr;" =>  "&#x112;",
		"{\\\= e}" =>  "&#x113;",
		"{\\\= E}" =>  "&#x112;",
		"&eogon;" =>  "&#x119;",
		"&Eogon;" =>  "&#x118;",
		"&gacute;" => "&#x1F5;",
		"&gbreve;" => "&#x11F;",
		"&Gbreve;" => "&#x11E;",
		"&Gcedil;" => "&#x122;",
		"&gcirc;" =>  "&#x11D;",
		"&Gcirc;" =>  "&#x11C;",
		"&gdot;" =>   "&#x121;",
		"&Gdot;" =>   "&#x120;",
		"&hcirc;" =>  "&#x125;",
		"&Hcirc;" =>  "&#x124;",
		"&hstrok;" => "&#x127;",
		"&Hstrok;" => "&#x126;",
		"&Idot;" =>   "&#x130;",
		"&Imacr;" =>  "&#x12A;",
		"&imacr;" =>  "&#x12B;",
		"{\\\= I}" =>  "&#x12A;",
		"{\\\= i}" =>  "&#x12B;",
		"{\\\= \\i}" =>  "&#x12B;",
		"\\={I}" =>  "&#x12A;",
		"\\={\\i}" =>  "&#x12B;",
		"&ijlig;" =>  "&#x133;",
		"&IJlig;" =>  "&#x132;",
		"&inodot;" => "&#x131;",
		"&iogon;" =>  "&#x12F;",
		"&Iogon;" =>  "&#x12E;",
		"&itilde;" => "&#x129;",
		"&Itilde;" => "&#x128;",
		"&jcirc;" =>  "&#x135;",
		"&Jcirc;" =>  "&#x134;",
		"&kcedil;" => "&#x137;",
		"&Kcedil;" => "&#x136;",
		"&kgreen;" => "&#x138;",
		"&lacute;" => "&#x13A;",
		"&Lacute;" => "&#x139;",
		"&lcaron;" => "&#x13E;",
		"&Lcaron;" => "&#x13D;",
		"&lcedil;" => "&#x13C;",
		"&Lcedil;" => "&#x13B;",
		"&lmidot;" => "&#x140;",
		"&Lmidot;" => "&#x139;",
		"\\l{}" => "&#x142;",
		"\\L{}" => "&#x141;",
		"&lstrok;" => "&#x142;",
		"&Lstrok;" => "&#x141;",
		"{\\l}" => "&#x142;",
		"{\\L}" => "&#x141;",
		"&nacute;" => "&#x144;",
		"&Nacute;" => "&#x143;",
		"&eng;" =>    "&#x14B;",
		"&ENG;" =>    "&#x14A;",
		"&napos;" =>  "&#x149;",
		"&ncaron;" => "&#x148;",
		"&Ncaron;" => "&#x147;",
		"&ncedil;" => "&#x146;",
		"&Ncedil;" => "&#x145;",
		"&odblac;" => "&#x151;",
		"&Odblac;" => "&#x150;",
		"&Omacr;" =>  "&#x14C;",
		"&omacr;" =>  "&#x14D;",
		"{\\\= O}" =>  "&#x14C;",
		"{\\\= o}" =>  "&#x14D;",
		"&oelig;" =>  "&#x153;",
		"{\\oe}" =>  "&#x153;",
		"&OElig;" =>  "&#x152;",
		"&Oslash;" => "&#216;",
		"&otilde;" => "&#245;",
		"&Otilde;" => "&#213;",
		"&racute;" => "&#x155;",
		"&Racute;" => "&#x154;",
		"&rcaron;" => "&#x159;",
		"\\v{r}" => "&#x159;",
		"&Rcaron;" => "&#x158;",
		"&rcedil;" => "&#x157;",
		"&Rcedil;" => "&#x156;",
		"&scirc;" =>  "&#x15C;",
		"&Scirc;" =>  "&#x15D;",
		"\\c{s}" => "&#x15F;",
		"\\c{S}" => "&#x15E;",
		"&tcaron;" => "&#x165;",
		"&Tcaron;" => "&#x164;",
		"\\v{S}" => "&#x160;",
		"\\v{s}" => "&#x161;",
		"{\\v S}" => "&#x160;",
		"{\\v s}" => "&#x161;",
		"\\'{S}" => "&#x158;",
		"\\'{s}" => "&#x15B;",
		"\\c{t}" => "&#x163;",
		"\\c{T}" => "&#x162;",
		"&tcedil;" => "&#x163;",
		"&Tcedil;" => "&#x162;",
		"&zcaron;" => "&#x17E;",
		"&Zcaron;" => "&#x17D;",
		"\\v{z}" => "&#x17E;",
		"\\v{Z}" => "&#x17D;",
		"{\\\\.z}" => "&#x17C;",
		"{\\\\.Z}" => "&#x17B;",
		"\\\\.{z}" => "&#x17C;",
		"\\\\.{Z}" => "&#x17B;",
		"&zdot;" =>   "&#x17C;",
		"&Zdot;" =>   "&#x17B;",

		"&quot;" => "&#34;",
		"&apos;" => "&#39;",
		"&amp;" => "&#38;",
		"&lt;" => "&#60;",
		"&gt;" => "&#62;",
		"&nbsp;" => "&#160;",
		"&iexcl;" => "&#161;",
		"&cent;" => "&#162;",
		"&pound;" => "&#163;",
		"&curren;" => "&#164;",
		"&yen;" => "&#165;",
		"&brvbar;" => "&#166;",
		"&sect;" => "&#167;",
		"&uml;" => "&#168;",
		"&copy;" => "&#169;",
		"&ordf;" => "&#170;",
		"&laquo;" => "&#171;",
		"&not;" => "&#172;",
		"&shy;" => "&#173;",
		"&reg;" => "&#174;",
		"&macr;" => "&#175;",
		"&deg;" => "&#176;",
		"&plusmn;" => "&#177;",
		"&sup2;" => "&#178;",
		"&sup3;" => "&#179;",
		"&acute;" => "&#180;",
		"&micro;" => "&#181;",
		"&para;" => "&#182;",
		"&middot;" => "&#183;",
		"&cedil;" => "&#184;",
		"&sup1;" => "&#185;",
		"&ordm;" => "&#186;",
		"&raquo;" => "&#187;",
		"&frac14;" => "&#188;",
		"&frac12;" => "&#189;",
		"&frac34;" => "&#190;",
		"&iquest;" => "&#191;",
		"&times;" => "&#215;",
		"&divide;" => "&#247;",
		"&Agrave;" => "&#192;",
		"&Aacute;" => "&#193;",
		"&Acirc;" => "&#194;",
		"&Atilde;" => "&#195;",
		"&Auml;" => "&#196;",
		"&Aring;" => "&#197;",
		"\\AA" => "Å",
		"{\\AA}" => "Å",
		"&AElig;" => "&#198;",
		"&Ccedil;" => "&#199;",
		"&Egrave;" => "&#200;",
		"&Eacute;" => "&#201;",
		"&Ecirc;" => "&#202;",
		"&Euml;" => "&#203;",
		"&Igrave;" => "&#204;",
		"&Iacute;" => "&#205;",
		"&Icirc;" => "&#206;",
		"&Iuml;" => "&#207;",
		"&ETH;" => "&#208;",
		"&Ntilde;" => "&#209;",
		"&Ograve;" => "&#210;",
		"&Oacute;" => "&#211;",
		"&Ocirc;" => "&#212;",
		"&Otilde;" => "&#213;",
		"&Ouml;" => "&#214;",
		"&Oslash;" => "&#216;",
		"&Ugrave;" => "&#217;",
		"&Uacute;" => "&#218;",
		"&Ucirc;" => "&#219;",
		"{\\\= u}" => "&#x16b;",
		"{\\\= U}" => "&#x16a;",
		"&Uuml;" => "&#220;",
		"&Yacute;" => "&#221;",
		"\\\'{Y}" => "&#221;",
		"{\\th}" => "þ",
		"\\th" => "þ",
		"&THORN;" => "&#222;",
		"{\\TH}" => "&#222;",
		"\\TH" => "&#222;",
		"{\\ss}" => "&#223;",
		"\\ss" => "&#223;",
		"&szlig;" => "&#223;",
		"&agrave;" => "&#224;",
		"&aacute;" => "&#225;",
		"&acirc;" => "&#226;",
		"&atilde;" => "&#227;",
		"&auml;" => "&#228;",
		"{\\aa}" => "&#229;",
		"&aring;" => "&#229;",
		"&aelig;" => "&#230;",
		"{\\ae}" => "&#230;",
		"&ccedil;" => "&#231;",
		"&egrave;" => "&#232;",
#		"&eacute;" => "&#233;",
		"&ecirc;" => "&#234;",
		"&euml;" => "&#235;",
		"&igrave;" => "&#236;",
		"&iacute;" => "&#237;",
		"&icirc;" => "&#238;",
		"&iuml;" => "&#239;",
		"&eth;" => "&#240;",
		"&ntilde;" => "&#241;",
		"&ograve;" => "&#242;",
		"&oacute;" => "&#243;",
		"&ocirc;" => "&#244;",
		"&otilde;" => "&#245;",
		"&ouml;" => "&#246;",
		"&oslash;" => "&#248;",
		"&ugrave;" => "&#249;",
		"\\'{u}" => "&#250;",
		"&ucirc;" => "&#251;",
		"&uuml;" => "&#252;",
		"&yacute;" => "&#253;",
		"\\\'{y}" => "&#253;",
		"{\\\'y}" => "&#253;",
		"\\\'y" => "&#253;",
		"&thorn;" => "&#254;",
		"&yuml;" => "&#255;",
		);
my $defaultSupDir = "~/public_html/supplementals/";
### END user customizable section

### Ctrl-C handler
sub quitHandler {
  print STDERR "\n# $progname fatal\t\tReceived a 'SIGINT'\n# $progname - exiting cleanly\n";
  exit;
}

### HELP Sub-procedure
sub Help {
  print STDERR "usage: $progname -h\t\t\t\t[invokes help]\n";
  print STDERR "       $progname -v\t\t\t\t[invokes version]\n";
  print STDERR "       $progname [-q] [-V <vol>] [-s <supDir>] filename(s)...\n";
  print STDERR "Options:\n";
  print STDERR "\t-q\tQuiet Mode (don't echo license)\n";
  print STDERR "\t-s <supDir>\tExplicitly assign supplemental directory (default: $defaultSupDir)\n";
  print STDERR "\t-V <volume>\tExplicitly assign volume as <volume>\n";
  print STDERR "\n";
  print STDERR "Will accept input on STDIN as a single file.\n";
  print STDERR "\n";
}

### VERSION Sub-procedure
sub Version {
  if (system ("perldoc $0")) {
    die "Need \"perldoc\" in PATH to print version information";
  }
  exit;
}

sub License {
  print STDERR "# Copyright 2005 \251 by Min-Yen Kan\n";
}

###
### MAIN program
###

my $cmdLine = $0 . " " . join (" ", @ARGV);
if ($#ARGV == -1) { 		        # invoked with no arguments, possible error in execution? 
  print STDERR "# $progname info\t\tNo arguments detected, waiting for input on command line.\n";  
  print STDERR "# $progname info\t\tIf you need help, stop this program and reinvoke with \"-h\".\n";
}

$SIG{'INT'} = 'quitHandler';
getopts ('hqs:vV:');

our ($opt_q, $opt_s, $opt_v, $opt_h, $opt_V);
# use (!defined $opt_X) for options with arguments
if (!$opt_q) { License(); }		# call License, if asked for
if ($opt_v) { Version(); exit(0); }	# call Version, if asked for
my $volume = (!defined $opt_V) ? "XX" : $opt_V;
if ($volume eq "XX") {		# guess volume if not given
  $ARGV[0] =~ /([A-Z]\d\d)[\-\.]/;
  $volume = $1;
}
my $supDir = (!defined $opt_s) ? $defaultSupDir : $opt_s;
if ($opt_h) { Help(); exit (0); }	# call help, if asked for

## standardize input stream (either STDIN on first arg on command line)
my $fh;
my $filename;
if ($filename = shift) {
 NEWFILE:
  if (!(-e $filename)) { die "# $progname crash\t\tFile \"$filename\" doesn't exist"; }
  open (*IF, $filename) || die "# $progname crash\t\tCan't open \"$filename\"";
  $fh = "IF";
} else {
  $filename = "<STDIN>";
  $fh = "STDIN";
}

print "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n";
print "<volume id=\"$volume\">\n";

my %h = ();
my $inAbstract = 0;
my $line = 0;
while (<$fh>) {
  $line++;
  if (/^\#/) { next; }			# skip comments
  elsif (/^\s+$/) { next; }		# skip blank lines
  else {
    if ($inAbstract == 1) {
      if (/(.*)\},$/) {
	$h{"abstract"} .= treatLatex($1);
	$inAbstract = 0;
      } else {
	$h{"abstract"} .= treatLatex($_);
      }
    }
    if (/\@([A-Za-z]+)\{(.+),/) { # new entry 
      %h = ();
      $h{"bibtype"} = lc(treatLatex($1));
      $h{"bibkey"} = treatLatex($2);
    } elsif (/^\}/) { # end of entry
      my $id = getID(\%h);
      my $software = checkSoftware($volume,$id);
      if ($software ne "") { $h{"software"} = $software; } 
      my $datasets = checkDatasets($volume,$id);
      if ($datasets ne "") { $h{"dataset"} = $datasets; } 
      process(\%h,2,$volume,$id);
    } elsif (/\btitle\s+=\s+\{(.+)\}/) {
      $h{"title"} = treatLatex($1);
    } elsif (/\babstract\s+=\s+\{(.+)\}/) {
      $h{"abstract"} = treatLatex($1);
    } elsif (/\babstract\s+=\s+\{(.+)/) {
      $h{"abstract"} = treatLatex($1) . "\n";
      $inAbstract = 1;
    } elsif (/\beditor\s+=\s+\{(.+)\}/) {
      $h{"editor"} = treatLatex($1);
    } elsif (/\bauthor\s+=\s+\{(.+)\}/) {
      $h{"author"} = treatLatex($1);
    } elsif (/\bbooktitle\s+=\s+\{(.+)\}/) {
      $h{"booktitle"} = treatLatex($1);
    } elsif (/\bmonth\s+=\s+\{(.+)\}/) {
      $h{"month"} = treatLatex($1);
    } elsif (/\byear\s+=\s+\{(.+)\}/) {
      $h{"year"} = treatLatex($1);
    } elsif (/\baddress\s+=\s+\{(.+)\}/) {
      $h{"address"} = treatLatex($1);
    } elsif (/\bpublisher\s+=\s+\{(.+)\}/) {
      $h{"publisher"} = treatLatex($1);
    } elsif (/\bpages\s+=\s+\{(.+)\}/) {
      $h{"pages"} = treatLatex($1);
    } elsif (/\burl\s+=\s+\{(.+)\}/) {
      $h{"url"} = treatLatex($1);
    }
  }
}
print "</volume>\n\n";

close ($fh);

if ($filename = shift) {
  goto NEWFILE;
}

###
### END of main program
###

sub getID {
  my $hashRef = shift @_;
  my %h = %{$hashRef};
  my $id = 0;
  my $prefix = "";
  if (!defined $h{"url"}) {
    print STDERR "No URL defined!";
  } else {
    $h{"url"} =~ /(...)\-(\d{1,4})$/;
    $prefix = $1;		# eg. C00
    $id = $2;			# eg. 1001
    if ($id < 100) {		# deal with volumes 
      my @elts = split (//,$id);
      if ($elts[0] eq "0") { $id .= "00"; }
      else { $id = ($id < 9) ? ($id * 1000) : ($id * 100); }
    }
  }
  return $id;
}

sub process {
  my $hashRef = shift @_;
  my $indent = shift @_;
  my $volume = shift @_;
  my $id = shift @_;
  my %h = %{$hashRef};
  my $s = "";

  foreach my $k ("title", "author", "editor", "booktitle", "month",
		 "year", "address", "publisher", "pages", "url", "abstract",
		 "software", "dataset", "bibtype", "bibkey") {

    if (defined $h{$k}) {
      if ($k eq "editor" || $k eq "author") { 
	my @elts = split(/ +and +/,$h{$k}); # split to individual author
	for (my $i = 0; $i <= $#elts; $i++) {
	  $s .= "  " . " " x $indent;
	  $s .= "<" . $k . ">";
	  # handle variants
	  if ($elts[$i] =~ /(.+), (.+)/) {
	    $s .= "<first>$2</first><last>$1</last>";
	  } else {
	    $s .= $elts[$i];
	  }
	  $s .= "</" . $k . ">\n";
	}
      } else {
	$s .= "  " . " " x $indent;
	$s .= "<" . $k . ">";
	$s .= $h{$k};
	$s .= "</" . $k . ">\n";
      }
    }
  }
  $s .= "  </paper>\n\n";
  $s = "  <paper id=\"$id\">\n" . $s;
  print $s;
}

sub treatLatex {
  $_ = shift @_;
  foreach my $entity (keys %entities) {
    # pattern we replace is quoted so that \ ^ . { } are not regex symbols 
    s/\Q$entity\E/$entities{$entity}/g;
  }
  if ($_ =~ /\\/) { print STDERR "XXXX $line " . $_ . "\n"; }
  while ($_ =~ /\{([A-Za-z]+)\}/) {
    s/\{([A-Za-z]+)\}/$1/;
  }
  $_;
}

sub checkSoftware {
  my $volume = shift @_;
  my $id = shift @_;
  my ($prefix, undef) = split (//,$volume);

  my $software = `ls $supDir/$prefix/$volume/$volume-$id.Software* 2>/dev/null`;
  chomp $software;
  $software =~ /\/([^\/]+)$/;
  $software = $1;
  if ($software ne "") { return $software; }
}

sub checkDatasets {
  my $volume = shift @_;
  my $id = shift @_;
  my ($prefix, undef) = split (//,$volume);

  my $datasets = `ls $supDir/$prefix/$volume/$volume-$id.Datasets* 2>/dev/null`;
  chomp $datasets;
  $datasets =~ /\/([^\/]+)$/;
  $datasets = $1;
  if ($datasets ne "") { return $datasets; }
}
