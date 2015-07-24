# encoding: UTF-8
require "rexml/document"
require "date"
require 'fileutils'

DOI_PREFIX="10.3115/v1"


def export_conference_papers_in_volume(volume, conf_tag)
	volumeIsWorkshop = (@volume.anthology_id[0] == 'W')

	valid_paper_series = []
	@papers = @volume.papers
	if volumeIsWorkshop
		paper_series = ('00'..'99').to_a
		@papers.each do |paper|
			valid_paper_series << paper.anthology_id[-2..-1]
		end
	else
		paper_series = ('000'..'999').to_a
		@papers.each do |paper|
			valid_paper_series << paper.anthology_id[-3..-1]
		end
	end
	paper_series = paper_series && valid_paper_series
	
	paper_series.each do |p|
		@paper = Paper.find_by_anthology_id(@volume.anthology_id + p.to_s)
		if @paper # Check if paper is found
			# First we check if the @paper is front matter, then we will add chair tags
			if @paper.anthology_id[-3..-1] == "000" || (@paper.anthology_id[-2..-1] == "00" && volumeIsWorkshop)
				chairs = @paper.people
				if chairs and chairs.any?
					# contributors must be the first element
					event_metadata = conf_tag.elements["event_metadata"]
					if event_metadata
						contributors = REXML::Element.new "contributors"
						event_metadata.previous_sibling = contributors
					else
						contributors = conf_tag.add_element "contributors"
					end
				    person_count = 1;
					chairs.each do |person|
						person_name = contributors.add_element "person_name", {"contributor_role"=>"chair"}
						if person_count==1
					    	person_name.attributes["sequence"] = "first"
					   	else
					    	person_name.attributes["sequence"] = "additional"
					   	end
					   	if person.first_name.strip!='' and person.last_name.strip!=''
						    given_name = person_name.add_element "given_name"
						    given_name.text = person.first_name
						    surname = person_name.add_element "surname"
						    surname.text = person.last_name
						else # Some authors only have surname
							surname = person_name.add_element "surname"
						    surname.text = person.last_name.strip!='' ? person.last_name : person.first_name
						end
					    person_count += 1
					end
				end
			else # Normal paper
				conference_paper = conf_tag.add_element "conference_paper"
				
				contributors = conference_paper.add_element "contributors"
				person_count = 1;
				@paper.people.each do |person|
					person_name = contributors.add_element "person_name", {"contributor_role"=>"author"}
					if person_count==1
					    person_name.attributes["sequence"] = "first"
					else
					    person_name.attributes["sequence"] = "additional"
					end
					if person.first_name.strip!='' and person.last_name.strip!=''
						given_name = person_name.add_element "given_name"
					    given_name.text = person.first_name
					    surname = person_name.add_element "surname"
					    surname.text = person.last_name
					else 
						surname = person_name.add_element "surname"
						surname.text = person.last_name.strip!='' ? person.last_name : person.first_name
					end
				    person_count += 1
				end
				
				if @paper.title
					titles = conference_paper.add_element "titles"
			    title = titles.add_element "title"
			    title.text = @paper.title.gsub(/&/u, "and")
				end
			
			    if @paper.year
			    	publication_date = conference_paper.add_element "publication_date"
			    	year = publication_date.add_element "year"
			    	year.text = @paper.year
			    end
		    
			    if @paper.pages
			    	first, last = @paper.pages.gsub(/–/u,'-').split("-") 
			    	if !last
			    		last = first
			    	end
				    pages = conference_paper.add_element "pages"
				    first_page = pages.add_element "first_page"
				    first_page.text = first
				    last_page = pages.add_element "last_page"
				    last_page.text = last
				end
			
			    doi_data = conference_paper.add_element "doi_data"
			    doi = doi_data.add_element "doi"
			    doi.text = DOI_PREFIX + "/" + @paper.anthology_id
			  	if @paper.url
				    resource = doi_data.add_element "resource"
				    resource.text = @paper.url
				end
			end 
		end # Finish one paper
	end # Finish all papers in the volume
end


def export_journal_papers_in_volume(volume, journal_tag)
	valid_paper_series = []
	@papers = @volume.papers

	paper_series = ('000'..'999').to_a
	@papers.each do |paper|
		valid_paper_series << paper.anthology_id[-3..-1]
	end
	
	paper_series = paper_series && valid_paper_series
	
	paper_series.each do |p|
		@paper = Paper.find_by_anthology_id(@volume.anthology_id + p.to_s)
		if @paper # Check if paper is found
			# First we check if the @paper is front matter, then we will add editor tags
			if @paper.anthology_id[-3..-1] == "000"
				editors = @paper.people
				if editors and editors.any?
					# contributors must be the first element
					journal_metadata = journal_tag.elements["journal_metadata"]
					if event_metadata
						contributors = REXML::Element.new "contributors"
						journal_metadata.previous_sibling = contributors
					else
						contributors = journal_tag.add_element "contributors"
					end
		
				    person_count = 1;
					editors.each do |person|
						person_name = contributors.add_element "person_name", {"contributor_role"=>"editor"}
						if person_coun==1
					    	person_name.attributes["sequence"] = "first"
					   	else
					    	person_name.attributes["sequence"] = "additional"
					   	end
					   	if person.first_name.strip!='' and person.last_name.strip!=''
						    given_name = person_name.add_element "given_name"
						    given_name.text = person.first_name
						    surname  = person_name.add_element "surname"
						    surname.text = person.last_name
						else
							surname = person_name.add_element "surname"
							surname.text = person.last_name.strip!='' ? person.last_name : person.first_name
						end
					    person_count += 1
					end
				end
			else # Normal article
				journal_article = journal_tag.add_element "journal_article"
				
				if @paper.title
					titles = journal_article.add_element "titles"
				    title = titles.add_element "title"
				    title.text = @paper.title
				end
				
				contributors = journal_article.add_element "contributors"
				person_count = 1;
				@paper.people.each do |person|
					person_name = contributors.add_element "person_name", {"contributor_role"=>"author"}
					if person_count==1
					    person_name.attributes["sequence"] = "first"
					else
					    person_name.attributes["sequence"] = "additional"
					end
				   	if person.first_name.strip!='' and person.last_name.strip!=''
						given_name = person_name.add_element "given_name"
					    given_name.text = person.first_name
					    surname  = person_name.add_element "surname"
					    surname.text = person.last_name
					else
						surname = person_name.add_element "surname"
						surname.text = person.last_name.strip!='' ? person.last_name : person.first_name
				   	end
				    person_count += 1
				end
				
			    if @paper.year
			    	publication_date = journal_article.add_element "publication_date"
			    	year = publication_date.add_element "year"
			    	year.text = @paper.year
			    end
				if @paper.pages
			    	first, last = @paper.pages.gsub(/–/u,"-").split("-") 
			    	if !last
			    		last = first
			    	end
				    pages = journal_article.add_element "pages"
				    first_page = pages.add_element "first_page"
				    first_page.text = first
				    last_page = pages.add_element "last_page"
				    last_page.text = last
				end
			
			    doi_data = journal_article.add_element "doi_data"
			    doi = doi_data.add_element "doi"
			    doi.text = DOI_PREFIX + "/" + @paper.anthology_id
			    timestamp = doi_data.add_element "timestamp"
	 			timestamp.text = Time.now.strftime('%Y%m%d%H%M%S')
	 			if @paper.url
				    resource = doi_data.add_element "resource"
				    resource.text = @paper.url
				end
			end 
		end # Finish one article
	end # Finish all articles in the volume
end


# conference or workshop
def export_conference_volume(volume, xml_body)
	conference = xml_body.add_element "conference"
	
	# event meta
	event_metadata = conference.add_element "event_metadata"
    conference_name = event_metadata.add_element "conference_name"
    conference_name.text = @volume.title #TODO: remove Proceedings of the 
    
    if @volume.address
    	conference_location = event_metadata.add_element "conference_location"
    	conference_location.text = @volume.address
    end
    conference_date = event_metadata.add_element "conference_date", 
    	{"start_year"=>@volume.year, "end_year"=>@volume.year, 
    	"start_month"=>Date::MONTHNAMES.index(@volume.month), 
    	"end_month"=>Date::MONTHNAMES.index(@volume.month)}
  
	# proceedings
	proceedings_metadata = conference.add_element "proceedings_metadata", {"language"=>"en"}
    proceedings_title = proceedings_metadata.add_element "proceedings_title"
    proceedings_title.text = @volume.title
    
    publisher = proceedings_metadata.add_element "publisher"
    publisher_name = publisher.add_element "publisher_name"
   	if @volume.publisher
    	publisher_name.text = @volume.publisher
   	else
    	publisher_name.text = "unknown"
   	end
    publisher_place = publisher.add_element "publisher_place"
    publisher_place.text = "Stroudsburg, PA, USA"

	publication_date = proceedings_metadata.add_element "publication_date"
    year = publication_date.add_element "year"
    year.text = @volume.year
    
   	proceedings_metadata.add_element "noisbn", {"reason"=>"simple_series"}
   	
    doi_data = proceedings_metadata.add_element "doi_data"
    doi = doi_data.add_element "doi"
    doi.text  = DOI_PREFIX + "/" + @volume.anthology_id
    timestamp = doi_data.add_element "timestamp"
    timestamp.text = Time.now.strftime('%Y%m%d%H%M%S')
    resource = doi_data.add_element "resource"
    resource.text = @volume.url
    
    export_conference_papers_in_volume(@volume, conference)
end


=begin
Extract volume and issue number from the title, e.g., the return value is [2,1] if the title is 
		"Transactions of the Association of Computational Linguistics – Volume 2, Issue 1"
=end
def get_volume_issue(volume_title)
	volume, issue = volume_title.split("-")[-1].strip().split(",")
	if volume
		volume_num = volume[-1]
	end
	if issue
		issue_num = issue[-1]
	else
		issue_num = 1
	end
	return volume_num, issue_num
end		


def export_tacl_volume(volume, xml_body)
	journal = xml_body.add_element "journal"
	
	# event meta
	journal_metadata  = journal.add_element "journal_metadata", {"language"=>"en"}
	full_title = journal_metadata .add_element "full_title"
	full_title.text  = @volume.title
	issn = journal_metadata.add_element "issn"
	issn.text = "2307-387X" # specifically for TACL

	journal_issue = journal.add_element "journal_issue"
	publication_date = journal_issue.add_element "publication_date"
	year = publication_date.add_element "year"
	year.text = @volume.year
	
	volume_num, issue_num = get_volume_issue(@volume.title)
	journal_volume = journal_issue.add_element "journal_volume"
	volume = journal_volume.add_element "volume"
	volume.text  = volume_num
	issue = journal_issue.add_element "issue"
	issue.text = issue_num
    
  	doi_data = journal_issue.add_element "doi_data"
  	doi = doi_data.add_element "doi"
  	doi.text  = DOI_PREFIX + "/" + @volume.anthology_id
  	timestamp = doi_data.add_element "timestamp"
  	timestamp.text = Time.now.strftime('%Y%m%d%H%M%S')
  	resource = doi_data.add_element "resource"
  	resource.text = @volume.url

  	export_journal_papers_in_volume(@volume, journal)	
end

# Some workshops should be excluded, although their publishers are ACL. 
def is_excluded_workshop(anthology_id)
	return anthology_id=='W15-01' || anthology_id=='W15-02' ||
		   anthology_id=='W15-03' || anthology_id=='W15-04' ||
		   anthology_id=='W15-18' || anthology_id=='W15-19' ||
		   anthology_id=='W15-20' || anthology_id=='W15-21' 
end

=begin
We assign DOI for conference/workshop/journal papers published by ACL since 2012.
P: ACL, D: EMNLP, E: EACL, N: NAACL, S: SemEval/Sem, W: Workshops by ACL, Q: TACL

Usage:
Please pass depositor's name and email as parameters
E.g., rake export:doi_single['name','namen@email.com']

=end
namespace :export do
  desc "Export each volume to a single doi"
	task :doi_single, [:name, :email] => :environment do |t, args|
		unless args.name or args.email
			abort("PLease pass depositor's name and email as parameters")
		end
		doi_depositor_name = args.name
    	doi_depositor_email = args.email
    
		#all_codes = ['A', 'C', 'D', 'E', 'F', 'H', 'I', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'W', 'X', 'Y']
		acl_codes = ['P', 'E', 'N', 'D', 'S', 'W', 'Q']
		
		current_year = Date.today.strftime('%y')
		years = ('12'..current_year).to_a
		volume_count = 1
		acl_codes.each do |c|
			years.each do |y|
				volume_found = false # by default, the anthology is empty
				if c == 'W' # If we have a workshop, the volume series will have 2 digits
					volume_series = ('01'..'99').to_a
				else # else, only count first digit
					volume_series = ('1'..'9').to_a
				end

				volume_series.each do |v|
					@volume = Volume.find_by_anthology_id(c + y + "-" + v.to_s)
					# Note: publisher is missing for some volumes in database.
					if @volume and @volume.publisher and @volume.publisher.include?('Association for Computational Linguistics') and not is_excluded_workshop(@volume.anthology_id)
						puts "Exporting volume " + @volume.anthology_id				

						xml_doc = REXML::Document.new  "<?xml version='1.0' encoding='UTF-8'?>"
					  	xml_batch = xml_doc.add_element "doi_batch", {"xmlns"=>"http://www.crossref.org/schema/4.3.5",
					                                  "xmlns:xsi"=>"http://www.w3.org/2001/XMLSchema-instance",
					                                  "xsi:schemaLocation"=>"http://www.crossref.org/schema/4.3.5 http://www.crossref.org/schema/deposit/crossref4.3.5.xsd",
					                                  "version"=>"4.3.5"}
					
					    # head
					    head = xml_batch.add_element "head"
						    
					    doi_batch_id = head.add_element "doi_batch_id"
					    doi_batch_id.text = volume_count.to_s.rjust(5, "0") # length is required to be at least 4 digits
					    timestamp = head.add_element "timestamp"
	  					timestamp.text = Time.now.strftime('%Y%m%d%H%M%S')
					    
					    depositor = head.add_element "depositor"
					    depositor_name = depositor.add_element "depositor_name"
					    depositor_name.text = doi_depositor_name
					    email = depositor.add_element "email_address"
					    email.text = doi_depositor_email
					    
					    registrant = head.add_element "registrant"
					    registrant.text = "Association for Computational Linguistics"
					    
					    body = xml_batch.add_element "body"

						
						if c == "Q"
							export_tacl_volume(@volume, body)
						else
							export_conference_volume(@volume, body)
						end

						# Write xml doc to xml file
						FileUtils.mkdir_p("export/doi")
						xml_file = File.new("export/doi/" + c + y + "-" + v.to_s + ".xml",'w:UTF-8')
						formatter = REXML::Formatters::Pretty.new(2)
    					formatter.compact = true # pretty-printing
    					xml_string = ""
    					formatter.write(xml_doc, xml_string)
						xml_string.gsub!(/amp;/, '') # delete all escape chars, &amp; => &
						xml_string.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
		
						xml_file.write xml_string
						xml_file.close
						volume_count += 1
					end # Finished one volume
				end # Finished all volumes
			end # finished exporting one anthology, Eg: "E12"
		end 
	end # task export
end