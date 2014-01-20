require 'tempfile'
require "rexml/document"

def export_papers_in_volume(volume, vol_tag)
	volumeIsWorkshop = (volume.anthology_id[0] == 'W')

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
		@paper = Paper.find_by_anthology_id(volume.anthology_id + p.to_s)
		if @paper # Check if paper is found
			pap = vol_tag.add_element 'paper', {"id" => @paper.anthology_id[-4..-1]} # Level 2 indentation
			# Level 3 indentation
			title = pap.add_element 'title'
			title.text = @paper.title

			person_count = 1;
			@paper.people.each do |person|
				# First we check if the @paper is front matter, then we will add editor tags
				if @paper.anthology_id[-3..-1] == "000" || (@paper.anthology_id[-2..-1] == "00" && volumeIsWorkshop)
					per = pap.add_element 'editor', {"id" => person_count}
				else # If it is not, we add author tags 
					per = pap.add_element 'author', {"id" => person_count}
				end
				first_name	= per.add_element 'first'
				last_name	= per.add_element 'last'
				first_name.text = person.first_name
				last_name.text 	= person.last_name
				person_count += 1
			end
			
			# Volumes do not have booktitles
			if not(@paper.anthology_id[-3..-1] == "000" || (@paper.anthology_id[-2..-1] == "00" && volumeIsWorkshop))
				booktitle = pap.add_element 'booktitle'
				booktitle.text = @volume.title
			end
			if @paper.month
				month = pap.add_element 'month'
				month.text = @paper.month
			end
			if @paper.year
				year = pap.add_element 'year'
				year.text = @paper.year
			end
			if @paper.address
				address = pap.add_element 'address'
				address.text = @paper.address
			end
			if @paper.publisher
				publisher = pap.add_element 'publisher'
				publisher.text = @paper.publisher
			end
			if @paper.pages
				pages = pap.add_element 'pages'
				pages.text = @paper.pages
			end
			if @paper.url
				url = pap.add_element 'url'
				url.text = @paper.url
			end
			if @paper.bibtype
				bibtype = pap.add_element 'bibtype'
				bibtype.text = @paper.bibtype
			end
			if @paper.bibkey
				bibkey = pap.add_element 'bibkey'
				bibkey.text = @paper.bibkey
			end
			if @paper.attachment != "none"
				if @paper.attach_type == "attachment"
					attachment = pap.add_element 'attachment'
					attachment.text = @paper.attachment
				elsif @paper.attach_type == "dataset"
					attachment = pap.add_element 'dataset'
					attachment.text = @paper.attachment
				elsif @paper.attach_type == "software"
					attachment = pap.add_element 'software'
					attachment.text = @paper.attachment
				end
			end
			# SIG and venue information for each volume will be put in the front matter paper
			if @paper.anthology_id[-3..-1] == "000" || (@paper.anthology_id[-2..-1] == "00" && volumeIsWorkshop)
				@volume.sigs.each do |sig|
					s = pap.add_element 'SIG', {'id' => sig.sigid}
					sig_name = s.add_element 'name'
					sig_name.text = sig.name
					sig_url = s.add_element 'url'
					sig_url.text = sig.url
				end
				@volume.events.each do |event|
					venue = Venue.find_by_id(event.venue_id)
					ven = pap.add_element 'venue', {'year' => event.year}
					ven_accronym = ven.add_element 'acronym'
					ven_accronym.text = venue.acronym
					ven_name = ven.add_element 'name'
					ven_name.text = venue.name
					ven_type = ven.add_element 'type'
					ven_type.text = venue.venue_type
				end
			end
		end # Finished one paper
	end # Finished all papers in the volume
end

# Export standard xml files
namespace :acl do
	desc "Export each anthology to a single xml file in the form E12.xml"
	task :export => :environment do
		
		codes = ['A', 'C', 'D', 'E', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R' 'S', 'T', 'U', 'W', 'X', 'Y']
		years = ('65'..'99').to_a + ('00'..'13').to_a
		codes.each do |c|
			years.each do |y|
				volume_found = false # by default, the anthology is empty
				xml_doc = REXML::Document.new "<?xml version='1.0'?>"
				vol = xml_doc.add_element 'volume', {"id" => c + y} # Level 1 indentation	
				if c == 'W' # If we have a workshop, the volume series will have 2 digits
					volume_series = ('01'..'99').to_a
				else # else, only count first digit
					volume_series = ('1'..'9').to_a
				end

				volume_series.each do |v|
					@volume = Volume.find_by_anthology_id(c + y + "-" + v.to_s)
					if @volume # Check if volume exists
						volume_found = true
						puts "Exporting volume " + @volume.anthology_id 	
						export_papers_in_volume(@volume, vol)	
					end # Finished one volume
				end # Finished all volumes

				export_loc = "#{Rails.root}/export/" + c + y + ".xml"
				if volume_found == true
					# Write xml doc to xml file
					xml_file = File.new("export/xml/" + c + y + ".xml",'w')
					xml_string = xml_doc.to_s
					xml_string.gsub!(/amp;/, '') # delete all escape chars, &amp; => &
					xml_string.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')

					xml_file.write xml_string
					xml_file.close
					puts "Saving file " + c + y + ".xml"
				end
			end # finished exporting one anthology, Eg: "E12"
		end 
	end # task export
end

# Export each volume to an individual xml file
namespace :acl do
	desc "Export each anthology to a single xml file in the form E12.xml"
	task :export_single_volume => :environment do
		codes = ['A', 'C', 'D', 'E', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R' 'S', 'T', 'U', 'W', 'X', 'Y']
		years = ('65'..'99').to_a + ('00'..'13').to_a
		codes.each do |c|
			years.each do |y|
				volume_found = false # by default, the anthology is empty
				if c == 'W' # If we have a workshop, the volume series will have 2 digits
					volume_series = ('01'..'99').to_a
				else # else, only count first digit
					volume_series = ('1'..'9').to_a
				end

				volume_series.each do |v|
					xml_doc = REXML::Document.new "<?xml version='1.0'?>"			
					vol = xml_doc.add_element 'volume', {"id" => c + y} # Level 1 indentation
					@volume = Volume.find_by_anthology_id(c + y + "-" + v.to_s)
					if @volume # Check if volume exists
						volume_found = true
						puts "Exporting volume " + @volume.anthology_id				

						export_papers_in_volume(@volume, vol)

						# Export the volume immediately
						export_loc = "#{Rails.root}/export/" + c + y + ".xml"
						if volume_found == true
							# Write xml doc to xml file
							xml_file = File.new("export/single/" + c + y + "-" + v.to_s + ".xml",'w')
							xml_string = xml_doc.to_s
							xml_string.gsub!(/amp;/, '') # delete all escape chars, &amp; => &
							xml_string.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')
			
							xml_file.write xml_string
							xml_file.close
							# puts "Saving file " + c + y + ".xml"
						end
					end # Finished one volume
				end # Finished all volumes

			end # finished exporting one anthology, Eg: "E12"
		end 
	end # task export
end


# Export all volumes to one single xml file
namespace :acl do
	desc "Export each anthology to a single xml file in the form E12.xml"
	task :export_all => :environment do
		
		codes = ['A', 'C', 'D', 'E', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R' 'S', 'T', 'U', 'W', 'X', 'Y']
		years = ('65'..'99').to_a + ('00'..'13').to_a
		xml_doc = REXML::Document.new "<?xml version='1.0'?>"
		acl = xml_doc.add_element 'aclanthology', {"version" => Time.now}

		codes.each do |c|
			years.each do |y|
				if c == 'W' # If we have a workshop, the volume series will have 2 digits
					volume_series = ('01'..'99').to_a
					@volume = Volume.find_by_anthology_id(c + y + "-01")
				else # else, only count first digit
					volume_series = ('1'..'9').to_a
					@volume = Volume.find_by_anthology_id(c + y + "-1")
				end

				# Only puts a tag if a volume does exist
				if @volume
					vol = acl.add_element 'volume', {"id" => c + y}
				else # if it doesn't, skip to next anthology
					next
				end
				
				volume_series.each do |v|
					@volume = Volume.find_by_anthology_id(c + y + "-" + v.to_s)
					if @volume # Check if volume exists
						puts "Exporting volume " + @volume.anthology_id 	
						export_papers_in_volume(@volume, vol)	
					end # Finished one volume
				end # Finished all volumes

				export_loc = "#{Rails.root}/export/" + c + y + ".xml"
			end # finished exporting one anthology, Eg: "E12"
		end 

		# Write xml doc to xml file
		xml_file = File.new("export/acl_anthology.xml",'w')
		xml_string = xml_doc.to_s
		xml_string.gsub!(/amp;/, "") # delete all escape chars, &amp; => &
		# xml_string.gsub!(/&rsquo;/, "'") # delete all escape chars
		xml_string.force_encoding('UTF-8').encode('UTF-8', :invalid => :replace, :undef => :replace, :replace => '')

		xml_file.write xml_string
		xml_file.close
		puts "Saving file acl_anthology.xml"
	end # task export_all
end