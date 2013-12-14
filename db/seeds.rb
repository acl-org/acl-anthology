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
puts "* * * * * * * * * * * * Deleting Old Data Start * * * * * * * * * * * *"
if not(Volume.delete_all and Paper.delete_all and Person.delete_all)
	puts "Error deleting databeses!"
end
puts "* * * * * * * * * * * * Deleting Old Data End * * * * * * * * * * * *"


puts "* * * * * * * * * * * * Seeding Data Start * * * * * * * * * * * *"
# currently for testing funtionality only
url = "http://aclweb.org/anthology/E/E12/E12.xml"

xml_data = Net::HTTP.get_response(URI.parse(url)).body
doc = REXML::Document.new xml_data
doc = doc.elements[1] # skipping the highest level tag


id = doc.attributes["id"] # The document id in the first "volume" tag, eg. E12
vol_id = id # temp for Paper
V = 0 # Number of volumes in the doc
(1..doc.size/2).each do |i| # Loop trough all the paper tags in the doc, has to be /2 because each tag is counted twice
	if doc.elements[i].attributes["id"][-2..-1] == "00" # Check if last 2 digits are 00, then it is a volume
		volume = Volume.new
		vol = doc.elements[i] # Short hand for easier reading
		volume.volume_id = id + '-' + vol.attributes["id"]
		vol_id = volume.volume_id
		volume.title = vol.elements[1].text
		j = 2
		while vol.elements[j].name == "editor"
			editor = Person.new
			# !!!!!!!!!!!!!!!!!Potential error!!!!!!!!!!!!!!!
			editor.first_name = vol.elements[j].elements[1].text
			editor.last_name = vol.elements[j].elements[2].text
			#editor.save # Save editor as person to database
			volume.people << editor # Save join person(editor) - volume to database
			j += 1
		end

		volume.month = vol.elements[j].text
		volume.year = (vol.elements[j+1].text).to_i 
		volume.address = vol.elements[j+2].text
		volume.publisher = vol.elements[j+3].text
		volume.url = vol.elements[j+4].text
		volume.bibtype = vol.elements[j+5].text
		volume.bibkey = vol.elements[j+6].text
		
		# SAVE VOLUME TO DB
		if volume.save == false
			puts ("Error saving volume " + volume.volume_id)
		end

		# SAVE EDITORS TO DB
		# SAVE RELATION OF THE 2 TO DB

		V += 1 # Increase number of volumes by 1
		P = 0 # Reset number of papers to 0
	else # If not, we assume it is a paper
		paper = Paper.new
		p = doc.elements[i]
		paper.volume_id = vol_id
		paper.paper_id = p.attributes["id"]
		paper.title = p.elements[1].text
		j = 2
		while p.elements[j].name == "author"
			author = Person.new
			# !!!!!!!!!!!!!!!!!Potential error!!!!!!!!!!!!!!!
			author.first_name = p.elements[j].elements[1].text
			author.last_name = p.elements[j].elements[2].text
	        #author.save # Save author as person to database
	        paper.people << author # Save join paper - person(author) to database
	    	j += 1    
	    end
		j += 1 # Skip the "booktitle" as it is the same as the volume booktitle
		paper.month = p.elements[j].text
		paper.year = p.elements[j+1].text
		paper.address = p.elements[j+2].text
		paper.publisher = p.elements[j+3].text
		if p.elements[j+4].name == "pages" # Only if there is a tag "pages" then add it
			paper.pages = p.elements[j+4].text
			j += 1
		end
		paper.url = p.elements[j+4].text
		paper.bibtype = p.elements[j+5].text
		paper.bibkey = p.elements[j+6].text

		if paper.save(:validate => false) == false
			puts ("Error saving paper " + vol_id + " " + paper.paper_id)
		end
		P += 1 # Increase papers of volumes by 1
	end
end

puts "* * * * * * * * * * * * Seeding Data End * * * * * * * * * * * *"
