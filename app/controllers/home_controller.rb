class HomeController < ApplicationController

  def index
  	message = "<strong>Dec 2013</strong><br> The
	<a href='U/U13'>Proceedings of the Australasian Language Technology Association Workshop 2013</a>
	and the 
	<a href='O/O13/''>Proceedings of the 25th Conference on Computational Linguistics and Speech Processing (ROCLING 2013)</a>
    are available on the ACL Anthology."
  	# flash[:alert] = 'Successfully checked in'
  	flash.now[:notice] = message.html_safe

  	@acronyms_acl = ["CL", "TACL", "ACL", "EACL", "NAACL", "SEMEVAL", "ANLP", "EMNLP", "WS"]
  	@acronyms_nonacl = ["COLING", "HLT", "IJCNLP", "LREC", "PACLIC", "ROCLING", "TINLAP", "ALTA", "RANLP", 
  		"JEP/TALN/RECITAL", "MUC", "TIPSTER"]

  	@years_acl = ["2014", "2013", "2012", "2011", "2010", 
  		"2009", "2008", "2007", "2006", "2005", "2004", "2003", "2002", "2001", "2000",
  		"1999", "1998", "1997", "1996", "1995", "1994", "1993", "1992", "1991", "1990",
  		"1989", "1988", "1987", "1986", "1985", "1984", "1983", "1982", "1981", "1980",
  		"1979"]
    @border_years_acl = ["2014", "2009", "1999", "1989"]

  	@years_nonacl = ["2014", "2013", "2012", "2011", "2010",
  		"2009", "2008", "2007", "2006", "2005", "2004", "2003", "2002", "2001", "2000",
  		"1999", "1998", "1997", "1996", "1995", "1994", "1993", "1992", "1991", "1990",
  		"1989", "1988", "1987", "1986", "1982", "1980",
  		"1978", "1975", "1973",
  		"1969", "1967", "1965"]
    @border_years_nonacl = ["2014", "2009", "1999", "1989", "1978"]

    @venues_acl = Venue.where(acronym: @acronyms_acl)
    @venues_nonacl = Venue.where(acronym: @acronyms_nonacl)

  	@sigs = Sig.all

    # Getting popular papers
    @popular_papers = []
    @popular_authors = []
    popular_papers_file =  "app/views/home/popular_papers.txt"
    popular_authors_file =  "app/views/home/popular_authors.txt"
    papers_file = File.open(popular_papers_file,'r')
    authors_file = File.open(popular_authors_file,'r')
    papers_file.each { |line| @popular_papers << line.strip }
    authors_file.each { |line| @popular_authors << line.strip }
  end
end
