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
	xml_data = Net::HTTP.get_response(URI.parse(url)).body
	xml_data.gsub!(/&/, '&amp;') # Remove illegal charactes
	doc = REXML::Document.new xml_data
	doc = doc.elements[1] # skipping the highest level tag


	id = doc.attributes["id"] # The document id in the first "volume" tag, eg. E12
	vol_id = id # temp for Paper
	num_of_vol = 0 # Number of volumes in the doc
	num_of_pap = 0
	(1..doc.size/2).each do |i| # Loop trough all the paper tags in the doc, has to be /2 because each tag is counted twice
		if doc.elements[i].attributes["id"][-3..-1] == "000" # Check if last 2 digits are 00, then it is a volume
			@volume = Volume.new
			vol = doc.elements[i] # Short hand for easier reading
			@volume.volume_id = id + '-' + vol.attributes["id"]
			vol_id = @volume.volume_id
			@volume.title = vol.elements['title'].text

			# Adding editor information
			vol.elements.each('editor') do |editor|
				first_name = ""
				last_name = ""
				if editor.elements['first'] || editor.elements['last'] # Check if there are first,last name tags 
					first_name = editor.elements['first'].text	if editor.elements['first']
					last_name = editor.elements['last'].text	if editor.elements['last']				
				else # If not, manually split the name into first name, last name
					name = editor.text
					first_name = name.split[0] # Only the first word in the full name
					last_name = name.split[1..-1].join(" ") # The rest of the full name			
				end
				@editor = Person.find_or_create_by_first_name_and_last_name(first_name, last_name)
				@volume.people << @editor # Save join person(editor) - volume to database
			end

			@volume.month 		= vol.elements['month'].text		if vol.elements['month']
			@volume.year 		= (vol.elements['year'].text).to_i	if vol.elements['year']
			@volume.address 	= vol.elements['address'].text		if vol.elements['address']
			@volume.publisher 	= vol.elements['publisher'].text	if vol.elements['publisher']
			@volume.url 		= vol.elements['url'].text			if vol.elements['url']
			@volume.bibtype 	= vol.elements['bibtype'].text		if vol.elements['bibtype']
			@volume.bibkey 		= vol.elements['bibkey'].text		if vol.elements['bibkey']

			# SAVE VOLUME TO DB
			if @volume.save! == false
				puts ("Error saving volume " + @volume.volume_id)
			end
			# SAVE EDITORS TO DB
			# SAVE RELATION OF THE 2 TO DB
			num_of_vol += 1 # Increase number of volumes by 1
			num_of_pap = 0 # Reset number of papers to 0
		else # If not, we assume it is a paper
			@paper = Paper.new
			p = doc.elements[i] # Short hand for easier reading
			@paper.volume_id = vol_id
			@paper.paper_id = p.attributes["id"]
			@paper.title = p.elements['title'].text

			p.elements.each('author') do |author|
				first_name = ""
				last_name = ""
				if author.elements['first'] || author.elements['last']# Check if there are first,last name tags 
					first_name = author.elements['first'].text 	if author.elements['first']
					last_name = author.elements['last'].text	if author.elements['last']
				else # If not, manually split the name into first name, last name
					name = author.text
					first_name = name.split[0] # Only the first word in the full name
					last_name = name.split[1..-1].join(" ") # The rest of the full name
				end
				@author = Person.find_or_create_by_first_name_and_last_name(first_name, last_name)
		        @paper.people << @author # Save join paper - person(author) to database
		    end

	    	@paper.month 		= p.elements['month'].text			if p.elements['month']
	    	@paper.year 		= (p.elements['year'].text).to_i	if p.elements['year']
	    	@paper.address 		= p.elements['address'].text		if p.elements['address']
	    	@paper.publisher 	= p.elements['publisher'].text		if p.elements['publisher']
	    	@paper.pages 		= p.elements['pages'].text			if p.elements['pages']
	    	@paper.url 			= p.elements['url'].text			if p.elements['url']
	    	@paper.bibtype 		= p.elements['bibtype'].text		if p.elements['bibtype']
	    	@paper.bibkey 		= p.elements['bibkey'].text			if p.elements['bibkey']

	    	if @paper.save(:validate => false) == false
	    		puts ("Error saving paper " + vol_id + " " + @paper.paper_id)
	    	end
			num_of_pap += 1 # Increase papers of volumes by 1
		end
	end
end

puts "* * * * * * * * * * Deleting Old Data Start  * * * * * * * * *"

if not(Volume.delete_all && Paper.delete_all && Person.delete_all)
	puts "Error deleting databeses!"
end

puts "* * * * * * * * * * Deleting Old Data End  * * * * * * * * * *"


puts "* * * * * * * * * * Seeding Data Start * * * * * * * * * * * *"

codes = ['A', 'C', 'D', 'E', 'H', 'I', 'L', 'M', 'N', 'P', 'S', 'T', 'X']
years = ('00'..'13').to_a + ('65'..'99').to_a
codes.each do |c|
	years.each do |y|
		if (c + y) == "C69" || (c + y) == "E03"
			next
		end
		url_string = "http://aclweb.org/anthology/" + c + '/' + c + y + '/' + c + y + ".xml"
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