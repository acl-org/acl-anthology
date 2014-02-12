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
require 'htmlentities'

def load_event(vol_id)
	case vol_id[0]
	when 'A'
		@venue = Venue.find_by_acronym("ANLP") # ACL events
	when 'C'
		@venue = Venue.find_by_acronym("COLING") # Non-ACL events
	when 'D'
		@venue = Venue.find_by_acronym("EMNLP") # ACL events
	when 'E'
		@venue = Venue.find_by_acronym("EACL") # ACL events
	when 'F'
		@venue = Venue.find_by_acronym("JEP/TALN/RECITAL") # ACL events
	when 'H'
		@venue = Venue.find_by_acronym("HLT") # Non-ACL events
	when 'I'
		@venue = Venue.find_by_acronym("IJCNLP") # Non-ACL events
	when 'J'
		@venue = Venue.find_by_acronym("CL") # ACL events
	when 'L'
		@venue = Venue.find_by_acronym("LREC") # Non-ACL events
	when 'M'
		@venue = Venue.find_by_acronym("MUC") # Non-ACL events
	when 'N'
		@venue = Venue.find_by_acronym("NAACL") # ACL events
	when 'O'
		@venue = Venue.find_by_acronym("ROCLING") # Non-ACL events
	when 'P'
		@venue = Venue.find_by_acronym("ACL") # ACL events
	when 'Q'
		@venue = Venue.find_by_acronym("TACL") # ACL events
	when 'R'
		@venue = Venue.find_by_acronym("RANLP") # Non-ACL events
	when 'S'
		@venue = Venue.find_by_acronym("SEMEVAL") # ACL events
	when 'T'
		@venue = Venue.find_by_acronym("TINLAP") # Non-ACL events
	when 'U'
		@venue = Venue.find_by_acronym("ALTA") # Non-ACL events
	when 'W'
		@venue = Venue.find_by_acronym("WS") # Workshops
	when 'X'
		@venue = Venue.find_by_acronym("TIPSTER") # Non-ACL events
	when 'Y'
		@venue = Venue.find_by_acronym("PACLIC") # Non-ACL events
	end
	year = ("20" + vol_id[1..2]).to_i if vol_id[1..2].to_i < 20
	year = ("19" + vol_id[1..2]).to_i if vol_id[1..2].to_i > 60
	@event = Event.find_or_create_by_venue_id_and_year(@venue.id, year)
	return @event
end

def load_volume_xml(url)
	xml_data = Net::HTTP.get_response(URI.parse(url)).body
	xml_data.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
	xml_data = HTMLEntities.new.decode xml_data # Change all escape characters to Unicode
	xml_data.gsub!(/&/, '&amp;') 
	xml_data.gsub!(/<</, '&lt;&lt;') 
	xml_data.gsub!(/>>/, '&gt;&gt;')
	xml_data.gsub!(/--/, '-') 

	doc = REXML::Document.new xml_data
	doc = doc.elements[1] # skipping the highest level tag

	id = doc.attributes["id"] # The document id in the first "volume" tag, eg. E12
	@curr_volume = Volume.new # Stores the current volume so the papers are saved to it

	# We will check if the xml is of a type workshop. If it is, each worshop ending with 00 will be treated as 1 volume
	w_check = "000" # default check for volumes
	w_num = -3 # default number of last chars checked (stands for 3)
	if id[0] == 'W'
		w_check = "00"
		w_num = -2
	end

	(1..doc.size/2).each do |i| # Loop trough all the paper tags in the doc, has to be /2 because each tag is counted twice
		if doc.elements[i].attributes["id"][w_num..-1] == w_check 
			vol = doc.elements[i] # Short hand for easier reading

			@volume = Volume.new
			if id[0] == 'W' # If the volume is a wrokshop, then use the first 2 digits of id
				@volume.anthology_id = id + '-' + vol.attributes["id"][0..1] # W12-01
			else # If not, only use the first digit
				@volume.anthology_id = id + '-' + vol.attributes["id"][0] # D13-1
			end
			@volume.title = vol.elements['title'].text if vol.elements['title']

			@front_matter = Paper.new
			@front_matter.anthology_id = id + '-' + vol.attributes["id"]
			@front_matter.title = @volume.title

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
					if full_name.split(',') == 2 # If the format is Last Name, First
						first_name = full_name.split(',')[1]
						last_name = full_name.split(',')[0]
					else # Splits "This Is Name" into "This Is" and "Name"
						first_name = full_name.split[0..-2].join(" ")
						last_name = full_name.split[-1]
					end
				end
				@editor = Person.find_or_create_by_first_name_and_last_name_and_full_name(first_name, last_name, full_name)
				@volume.people << @editor # Save join person(editor) - volume to database
				@front_matter.people << @editor
			end

			@volume.month 		= vol.elements['month'].text		if vol.elements['month']
			if vol.elements['year']
				@volume.year 	= (vol.elements['year'].text).to_i
			else
				@volume.year 	= ("20" + id[1..2]).to_i if id[1..2].to_i < 20
				@volume.year 	= ("19" + id[1..2]).to_i if id[1..2].to_i > 60
			end
			@volume.address 	= vol.elements['address'].text		if vol.elements['address']
			@volume.publisher 	= vol.elements['publisher'].text	if vol.elements['publisher']
			@volume.url 		= "http://aclweb.org/anthology/" + @volume.anthology_id
			@volume.bibtype 	= vol.elements['bibtype'].text		if vol.elements['bibtype']
			@volume.bibkey 		= vol.elements['bibkey'].text		if vol.elements['bibkey']

			@volume.save # Save volume
			@curr_volume = @volume

			@front_matter.month		= @volume.month
			@front_matter.year		= @volume.year
			@front_matter.address	= @volume.address
			@front_matter.publisher	= @volume.publisher
			@front_matter.url		= "http://aclweb.org/anthology/" + @front_matter.anthology_id
			@front_matter.bibtype	= @volume.bibtype
			@front_matter.bibkey	= @volume.bibkey
			@front_matter.attachment	= "none"
			@front_matter.attach_type	= "none"

			@curr_volume.papers << @front_matter # Save front_matter
			
			event = load_event(id)
			event.volumes << @volume
			
		else # If not, we assume it is a paper
			p = doc.elements[i] # Short hand for easier reading

			@paper = Paper.new
			@paper.anthology_id = id + '-' + p.attributes["id"] # D13-1001
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
			@paper.url 			= "http://aclweb.org/anthology/" + @paper.anthology_id
			@paper.bibtype 		= p.elements['bibtype'].text		if p.elements['bibtype']
			@paper.bibkey 		= p.elements['bibkey'].text			if p.elements['bibkey']
			
			@paper.attachment	= "none" # By default set this to none, for easy indexing
			@paper.attach_type	= "none" # By default set this to none, for easy indexing
			if p.elements['attachment']
				@paper.attachment	= p.elements['attachment'].text
				@paper.attach_type	= "attachment"
			end
			if p.elements['dataset']
				@paper.attachment	= p.elements['dataset'].text
				@paper.attach_type	= "dataset"
			end
			if p.elements['software']
				@paper.attachment	= p.elements['software'].text
				@paper.attach_type	= "software"
			end

			@curr_volume.papers << @paper	
		end
	end
end

def load_sigs(url)
	yaml_data = Net::HTTP.get_response(URI.parse(url)).body
	yml = YAML::load(yaml_data)
	@sig = Sig.new
	@sig.name	= yml["Name"]
	@sig.sigid	= yml["ShortName"]
	@sig.url	= yml["URL"]
	@sig.save
	yml["Meetings"].each do |meeting|
		keys = meeting.keys
		keys.each do |key|
			meeting[key].each do |anthology_id|
				if anthology_id.is_a? String
					@vol = Volume.find_by_anthology_id(anthology_id[0..-4])
					# anthology_id of volumes with bib_type is stored differently, with last 00 stripped (for workshops)
					@vol_bib = Volume.find_by_anthology_id(anthology_id[0..-3])
					if @vol
						@sig.volumes << @vol
					elsif @vol_bib
						@sig.volumes << @vol_bib
					end
				end
			end
		end
	end
end

def load_venues()
	Venue.create(acronym: 'CL', name: 'Computational Linguistics Journal', venue_type: 'ACL')
	Venue.create(acronym: 'TACL', name: 'Transactions of the Association of the Computational Linguistics', venue_type: 'ACL')
	Venue.create(acronym: 'ACL', name: 'ACL Annual Meeting', venue_type: 'ACL')
	Venue.create(acronym: 'EACL', name: 'European Chapter of ACL', venue_type: 'ACL')
	Venue.create(acronym: 'NAACL', name: 'North American Chapter of ACL', venue_type: 'ACL')
	Venue.create(acronym: 'SEMEVAL', name: 'Lexical and Computational Semantics and Semantic Evaluation (formerly Workshop on Sense Evaluation)', venue_type: 'ACL')
	Venue.create(acronym: 'ANLP', name: 'Applied Natural Language Processing Conference', venue_type: 'ACL')
	Venue.create(acronym: 'EMNLP', name: 'Conference on Empirical Methods in Natural Language Processing (and forerunners)', venue_type: 'ACL')
	Venue.create(acronym: 'WS', name: 'Workshops', venue_type: 'ACL')

	Venue.create(acronym: 'COLING', name: 'Int\'l Committee on Computational Linguistics (ICCL) Conf.', venue_type: 'Non ACL')
	Venue.create(acronym: 'HLT', name: 'Human Language Technology Conf.', venue_type: 'Non ACL')
	Venue.create(acronym: 'IJCNLP', name: 'Int\'l Joint Conf. on Natural Language Processing (and workshops)', venue_type: 'Non ACL')
	Venue.create(acronym: 'LREC', name: 'International Conference on Language Resources and Evaluation', venue_type: 'Non ACL')
	Venue.create(acronym: 'PACLIC', name: 'Pacific Asia Conference on Language, Information and Computation', venue_type: 'Non ACL')
	Venue.create(acronym: 'ROCLING', name: 'Rocling Computation Linguistics Conference and Journal', venue_type: 'Non ACL')
	Venue.create(acronym: 'TINLAP', name: 'Theoretical Issues In Natural Language Processing', venue_type: 'Non ACL')
	Venue.create(acronym: 'ALTA', name: 'Australasian Language Technology Association Workshop', venue_type: 'Non ACL')
	Venue.create(acronym: 'RANLP', name: 'International Conference Recent Advances in Natural Language Processing', venue_type: 'Non ACL')
	Venue.create(acronym: 'JEP/TALN/RECITAL', name: 'JEP/TALN/RECITAL', venue_type: 'Non ACL')
	Venue.create(acronym: 'MUC', name: 'Message Understanding Conf.', venue_type: 'Non ACL')
	Venue.create(acronym: 'TIPSTER', name: 'NIST\'s TIPSTER Text Program', venue_type: 'Non ACL')
end

puts "* * * * * * * * * * Deleting Old Data Start  * * * * * * * * *"

if not(Volume.delete_all && Paper.delete_all && Person.delete_all && Sig.delete_all && Event.delete_all && Venue.delete_all)
	puts "Error deleting databeses!"
end

puts "* * * * * * * * * * Deleting Old Data End  * * * * * * * * * *"


puts "* * * * * * * * * * Seeding Data Start * * * * * * * * * * * *"



# Seed Venues
puts "Started seeding Venues"
load_venues()
puts "Done seeding Venues"


# Seed Volumes + Papers
puts "Started seeding Volumes"
codes = ['A', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'W', 'X', 'Y']#['D', 'E', 'P', 'W']#
years = ('65'..'99').to_a + ('00'..'13').to_a
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
			load_volume_xml(url_string)
		end
		#test = Net::HTTP.get_response(URI.parse(url))
		
	end
end
puts "Done seeding Volumes"
puts "* * * * * * * * * * Seeding Data End * * * * * * * * * * * * *"

# Seed Venues
puts "Started seeding Venues"

puts "Done seeding Venues"

# Seed SIGs
puts "Started seeding SIGs"
sigs = ['sigann', 'sigbiomed', 'sigdat', 'sigdial', 'sigfsm', 'siggen', 'sighan', 'sighum', 'siglex', 
	'sigmedia', 'sigmol', 'sigmt', 'signll', 'sigparse', 'sigmorphon', 'sigsem', 'semitic', 'sigslpat', 'sigwac']
sigs.each do |sig|
	url_string = "http://aclweb.org/anthology/" + sig + ".yaml"
	url = URI.parse(url_string)
	request = Net::HTTP.new(url.host, url.port)
	response = request.request_head(url.path)
	if response.kind_of?(Net::HTTPOK)
		puts ("Seeding: " + url_string)
		load_sigs(url_string)
	end
end
puts "Done seeding SIGs"
