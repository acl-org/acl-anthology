class HomeController < ApplicationController

  def index
  	message = File.read("app/views/home/_message.html")
    # Written in html
  	flash.now[:notice] = message.html_safe

  	@years_acl = ["2019","2018","2017","2016","2015", "2014", "2013", "2012", "2011", "2010", 
  		"2009", "2008", "2007", "2006", "2005", "2004", "2003", "2002", "2001", "2000",
  		"1999", "1998", "1997", "1996", "1995", "1994", "1993", "1992", "1991", "1990",
  		"1989", "1988", "1987", "1986", "1985", "1984", "1983", "1982", "1981", "1980",
  		"1979"]
    @border_years_acl = ["2019", "2009", "1999", "1989"]

  	@years_nonacl = ["2019","2018","2017","2016","2015", "2014", "2013", "2012", "2011", "2010",
  		"2009", "2008", "2007", "2006", "2005", "2004", "2003", "2002", "2001", "2000",
  		"1999", "1998", "1997", "1996", "1995", "1994", "1993", "1992", "1991", "1990",
  		"1989", "1988", "1987", "1986", "1982", "1980",
  		"1978", "1975", "1973",
  		"1969", "1967", "1965"]
    @border_years_nonacl = ["2019", "2009", "1999", "1989", "1978"]

    # If only a certain list of venues need to showed
    @acronyms_acl = ["CL", "TACL", "ACL", "EACL", "NAACL", "*SEMEVAL", 
                     "EMNLP", "CONLL", "ANLP", "WS"]
    @acronyms_nonacl = ["COLING", "HLT", "IJCNLP", "LREC", "PACLIC", "ROCLING/IJCLCLP", "ALTA", "RANLP", 
      "JEP/TALN/RECITAL", "MUC", "TIPSTER", "TINLAP"]
    @venues_acl = Venue.where(acronym: @acronyms_acl)
    @venues_nonacl = Venue.where(acronym: @acronyms_nonacl)
    
    # If all venues need to be shown on the index page
    # @venues_acl = Venue.where(venue_type: "ACL")
    # @venues_nonacl = Venue.where(venue_type: "Non ACL")
    @sigs = Sig.all

    # Getting popular papers
    @popular_papers = []
    @popular_authors = []
    popular_papers_file =  "db/popular_papers.txt"
    popular_authors_file =  "db/popular_authors.txt"
    papers_file = File.open(popular_papers_file,'r')
    authors_file = File.open(popular_authors_file,'r')
    papers_file.each { |line| @popular_papers << line.strip }
    authors_file.each { |line| @popular_authors << line.strip }
  end
end
