# This file should contain all the record creation needed to seed the database with its default values.
# The data can then be loaded with the rake db:seed (or created alongside the db with db:setup).
#
# Examples:
#
#   cities = City.create([{ name: 'Chicago' }, { name: 'Copenhagen' }])
#   Mayor.create(name: 'Emanuel', city: cities.first)

# This file is used to seed all the data from the xml files to the database
# To run use:
# $ rake db:seed
# On Heroku remote server:
# $ heroku run rake db:seed


# External library used to load and work with xml files:
# http://www.germane-software.com/software/rexml/docs/tutorial.html
require "rexml/document"
require "net/http"
require "uri"

def extract(url)
	@sigann = Sig.find_by_sigid('SIGANN') ##########################################################
	@venueacl = Venue.find_by_venueid('ACL') ##########################################################

	xml_data = Net::HTTP.get_response(URI.parse(url)).body
	xml_data.gsub!(/&/, '&amp;') # Remove illegal charactes
	xml_data.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
	doc = REXML::Document.new xml_data
	doc = doc.elements[1] # skipping the highest level tag

	id = doc.attributes["id"] # The document id in the first "volume" tag, eg. E12
	vol_id = id # temp for Paper
	num_of_vol = 0 # Number of volumes in the doc
	num_of_pap = 0
	@curr_volume = Volume.new # Will store the current volume so the papers are saved to it
	# We will check if the xml is of a type workshop. If it is, each worshop ending with 00 will be treated as 1 volume
	w_check = "000" # default check for volumes
	w_num = -3 # default number of last chars checked (stands for 3)
	if id[0] == 'W'
		w_check = "00"
		w_num = -2
	end

	(1..doc.size/2).each do |i| # Loop trough all the paper tags in the doc, has to be /2 because each tag is counted twice
		# Check if last 2 digits are 000, then it is a volume. if it is workshop then w_check = "00"
		if doc.elements[i].attributes["id"][w_num..-1] == w_check 
			@volume = Volume.new
			vol = doc.elements[i] # Short hand for easier reading
			@volume.anthology_id = id + '-' + vol.attributes["id"]
			vol_id = @volume.anthology_id
			#puts vol_id ##########################################################
			@volume.title = vol.elements['title'].text if vol.elements['title']

			# Adding editor information
			vol.elements.each('editor') do |editor|
				first_name = ""
				last_name = ""
				full_name = ""
				if editor.elements['first'] || editor.elements['last'] # Check if there are first,last name tags 
					first_name = editor.elements['first'].text	if editor.elements['first']
					last_name = editor.elements['last'].text	if editor.elements['last']
					first_name = "" if first_name == nil
					last_name = "" if last_name == nil
					full_name = first_name + " " + last_name
				else # If not, manually split the name into first name, last name
					full_name = editor.text
					first_name = full_name.split[0] # Only the first word in the full name
					last_name = full_name.split[1..-1].join(" ") # The rest of the full name			
				end
				@editor = Person.find_or_create_by_first_name_and_last_name_and_full_name(first_name, last_name, full_name)
				@volume.people << @editor # Save join person(editor) - volume to database
			end

			@volume.month 		= vol.elements['month'].text		if vol.elements['month']
			if vol.elements['year']
				@volume.year 	= (vol.elements['year'].text).to_i
			else
				@volume.year 	= ("20" + id[1..3]).to_i if id[1..3].to_i < 20
				@volume.year 	= ("19" + id[1..3]).to_i if id[1..3].to_i > 60
			end
			@volume.address 	= vol.elements['address'].text		if vol.elements['address']
			@volume.publisher 	= vol.elements['publisher'].text	if vol.elements['publisher']
			@volume.url 		= vol.elements['url'].text			if vol.elements['url']
			@volume.bibtype 	= vol.elements['bibtype'].text		if vol.elements['bibtype']
			@volume.bibkey 		= vol.elements['bibkey'].text		if vol.elements['bibkey']

			# SAVE VOLUME TO DB
			@sigann.volumes << @volume ##########################################################
			@venueacl.volumes << @volume ##########################################################
			# if @volume.save! == false
			# 	puts ("Error saving volume " + @volume.anthology_id)
			# end
			@curr_volume = @volume
			# SAVE EDITORS TO DB
			# SAVE RELATION OF THE 2 TO DB
			num_of_vol += 1 # Increase number of volumes by 1
			num_of_pap = 0 # Reset number of papers to 0
		else # If not, we assume it is a paper
			@paper = Paper.new
			p = doc.elements[i] # Short hand for easier reading
			@paper.anthology_id = vol_id
			@paper.paper_id = p.attributes["id"]
			#puts @paper.paper_id ##########################################################

			@paper.title = p.elements['title'].text

			p.elements.each('author') do |author|
				first_name = ""
				last_name = ""
				full_name = ""
				if author.elements['first'] || author.elements['last']# Check if there are first,last name tags 
					first_name = author.elements['first'].text 	if author.elements['first']
					last_name = author.elements['last'].text	if author.elements['last']
					first_name = "" if first_name == nil
					last_name = "" if last_name == nil
					full_name = first_name + " " + last_name
				else # If not, manually split the name into first name, last name
					full_name = author.text
					first_name = full_name.split[0] # Only the first word in the full name
					last_name = full_name.split[1..-1].join(" ") # The rest of the full name
				end
				@author = Person.find_or_create_by_first_name_and_last_name_and_full_name(first_name, last_name, full_name)
		        @paper.people << @author # Save join paper - person(author) to database
		    end

	    	@paper.month 		= p.elements['month'].text			if p.elements['month']
	    	if p.elements['year']
				@paper.year 	= (p.elements['year'].text).to_i
			else
				@paper.year 	= ("20" + id[1..3]).to_i if id[1..3].to_i < 20
				@paper.year 	= ("19" + id[1..3]).to_i if id[1..3].to_i > 60
			end
	    	@paper.address 		= p.elements['address'].text		if p.elements['address']
	    	@paper.publisher 	= p.elements['publisher'].text		if p.elements['publisher']
	    	@paper.pages 		= p.elements['pages'].text			if p.elements['pages']
	    	@paper.url 			= p.elements['url'].text			if p.elements['url']
	    	@paper.bibtype 		= p.elements['bibtype'].text		if p.elements['bibtype']
	    	@paper.bibkey 		= p.elements['bibkey'].text			if p.elements['bibkey']

	    	@curr_volume.papers << @paper
	    	
			num_of_pap += 1 # Increase papers of volumes by 1
		end
	end
end

puts "* * * * * * * * * * Deleting Old Data Start  * * * * * * * * *"

if not(Volume.delete_all && Paper.delete_all && Person.delete_all && Sig.delete_all)
	puts "Error deleting databeses!"
end

puts "* * * * * * * * * * Deleting Old Data End  * * * * * * * * * *"


puts "* * * * * * * * * * Seeding Data Start * * * * * * * * * * * *"

# Seeding SIGs
Sig.create(name: 'Special Interest Group for Annotation', sigid: 'SIGANN', url: 'http://www.cs.vassar.edu/sigann/')
Sig.create(name: 'Special Interest Group on Biomedical Natural Language Processing', sigid: 'SIGBIOMED', url: 'http://aclweb.org/anthology/sigbiomed.html')
Sig.create(name: 'Special Interest Group on Linguistic data and corpus-based approaches to NLP', sigid: 'SIGDAT', url: 'http://www.sigdat.org/')
Sig.create(name: 'Special Interest Group on Dialogue', sigid: 'SIGDIAL', url: 'http://www.sigdial.org/')
Sig.create(name: 'Special Interest Group on Finite-State Methods', sigid: 'SIGFSM', url: 'http://aclweb.org/anthology/sigfsm.html')
Sig.create(name: 'Special Interest Group on Natural Language Generation', sigid: 'SIGGEN', url: 'http://www.siggen.org/')
Sig.create(name: 'Special Interest Group on Chinese Language Processing', sigid: 'SIGHAN', url: 'http://www.sighan.org/')
Sig.create(name: 'Special Interest Group on Language Technologies for the Socio-Economic Sciences and Humanities', sigid: 'SIGHUM', url: 'http://aclweb.org/anthology/sighum.html')
Sig.create(name: 'Special Interest Group on the Lexicon', sigid: 'SIGLEX', url: 'http://www.clres.com/siglex.html')
Sig.create(name: 'Special Interest Group on Multimedia Language Processing', sigid: 'SIGMEDIA', url: 'http://mm-werkstatt.informatik.uni-augsburg.de/projects/sigmedia/')
Sig.create(name: 'Association for Mathematics of Language', sigid: 'SIGMOL', url: 'http://molweb.org/')
Sig.create(name: 'Special Interest Group for Machine Translation', sigid: 'SIGMT', url: 'http://www.sigmt.org/')
Sig.create(name: 'Special Interest Group on Natural Language Learning', sigid: 'SIGNLL', url: 'http://aclweb.org/anthology/signll.html')
Sig.create(name: 'Special Interest Group on Natural Language Parsing', sigid: 'SIGPARSE', url: 'http://www.cs.cmu.edu/~sigparse/')
Sig.create(name: 'Special Interest Group on Computational Morphology and Phonology', sigid: 'SIGMORPHON', url: 'http://aclweb.org/anthology/sigmorphon.html')
Sig.create(name: 'Special Interest Group on Computational Semantics', sigid: 'SIGSEM', url: 'http://www.sigsem.org/wiki/Main_Page')
Sig.create(name: 'Special Interest Group on Computational Approaches to Semitic Languages', sigid: 'SEMITIC', url: 'http://cl.haifa.ac.il/semitic/')
Sig.create(name: 'Special Interest Group on Speech and Language Processing for Assistive Technologies', sigid: 'SIGSLPAT', url: 'http://www.slpat.org/')
Sig.create(name: 'Special Interest Group on Web as Corpus', sigid: 'SIGWAC', url: 'http://www.sigwac.org.uk/')

Venue.create(acronym: 'ACL', name: 'ACL Annual Meeting', venueid: 'ACL')

codes = ['A', 'C', 'D', 'E', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R' 'S', 'T', 'U', 'W', 'X', 'Y']
years = ('00'..'13').to_a + ('65'..'99').to_a
codes.each do |c|
	years.each do |y|
		url_string = "http://aclweb.org/anthology/" + c + '/' + c + y + '/' + c + y + ".xml"
		# For single link test
		# url_string = "http://aclweb.org/anthology/H/H01/H01.xml"
		url = URI.parse(url_string)
		request = Net::HTTP.new(url.host, url.port)
		response = request.request_head(url.path)
		if response.kind_of?(Net::HTTPOK)
			puts ("Seeding: " + url_string)
			extract(url_string)
		end
		#test = Net::HTTP.get_response(URI.parse(url))
		
	end
end

# currently for testing funtionality only
# url = "http://aclweb.org/anthology/C/C65/C65.xml"



puts "* * * * * * * * * * Seeding Data End * * * * * * * * * * * * *"





