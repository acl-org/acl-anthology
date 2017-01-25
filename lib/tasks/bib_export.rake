require "rexml/document"

# runs command, prints stdout only if command fails
def run_cmd_quietly cmd
  output = `#{cmd}`
  if (!$?.success?)
    print "#{cmd}\n"
    print output
  end
end

def export_volume_mods volume
	dash = /[–-]+/
	papers = volume.papers
	volume_title = volume.title
	year = volume.year
	authors = volume.people
	xml = REXML::Document.new "<?xml version='1.0'?>"
	mods=xml.add_element 'modsCollection', {"version" => Time.now}
	title_info = mods.add_element 'titleInfo'
	title_name = title_info.add_element 'title'
	title_name.text = volume_title
	authors.each do |author|
		name = mods.add_element 'name'
		name.attributes["type"]="personal"

		name_part_first = name.add_element 'namePart'
		name_part_first.attributes["type"]="given"
		name_part_first.text = author.first_name

		name_part_last = name.add_element 'namePart'
		name_part_last.attributes["type"]="family"
		name_part_last.text = author.last_name

		role = name.add_element 'role'
		roleterm = role.add_element 'roleTerm'
		roleterm.attributes["authority"]="marcrelator"
		roleterm.attributes["type"]="text"
		roleterm.text="editor"
	end

	origin_info = mods.add_element 'originInfo'
	if volume.publisher
		publisher = origin_info.add_element 'publisher'
		publisher.text = volume.publisher
	end
	if volume.address or volume.url
		volume_location = mods.add_element 'location'
		if volume.address
			volume_address = volume_location.add_element 'physicalLocation'
			volume_address.text = volume.address
		end
		if volume.url
			volume_url = volume_location.add_element 'url'
			volume_url.text = volume.url
		end
	end
	date_issued = origin_info.add_element 'dateIssued'
	date_issued.text = year

	papers.each do |paper|
		if (!((paper.anthology_id[0] == "W" and paper.anthology_id[-2..-1] == "00") or paper.anthology_id[-3..-1] == "000"))
			paper_mods=mods.add_element 'mods'
			paper_mods.attributes["ID"]=paper.anthology_id

			paper_title_info = paper_mods.add_element 'titleInfo'
			paper_title_name = paper_title_info.add_element 'title'
			paper_title_name.text = paper.title
			paper.people.each { |paper_author|
				paper_name = paper_mods.add_element 'name'
				paper_name.attributes["type"]="personal"

				paper_name_part_first = paper_name.add_element 'namePart'
				paper_name_part_first.attributes["type"]="given"
				paper_name_part_first.text = paper_author.first_name

				paper_name_part_last = paper_name.add_element 'namePart'
				paper_name_part_last.attributes["type"]="family"
				paper_name_part_last.text = paper_author.last_name

				paper_role = paper_name.add_element 'role'
				paper_roleterm = paper_role.add_element 'roleTerm'
				paper_roleterm.attributes["authority"]="marcrelator"
				paper_roleterm.attributes["type"]="text"
				paper_roleterm.text="author"
			}

			if (paper.doi) 
			   	identifier = mods.add_element 'identifier'
				identifier.attributes["type"] = "DOI"
				identifier.text = paper.doi
			end

			if (paper.pages)
				part = paper_mods.add_element 'part'
				extent = part.add_element 'extent'
				extent.attributes['unit'] = 'pages'
				startPage = extent.add_element 'start'
				startPage.text = paper.pages.split(dash)[0]
				endPage = extent.add_element 'end'
				endPage.text = paper.pages.split(dash)[1]
			end


			paper_origin_info = paper_mods.add_element 'originInfo'
			if paper.publisher
				paper_publisher = paper_origin_info.add_element 'publisher'
				paper_publisher.text = paper.publisher
			end
			paper_date_issued = paper_origin_info.add_element 'dateIssued'
			paper_date_issued.text = paper.year

			if paper.address or paper.url
				paper_location = paper_mods.add_element 'location'
				if paper.url
					paper_url = paper_location.add_element 'url'
					paper_url.text = paper.url
				end
				if paper.address
					paper_address = paper_location.add_element 'physicalLocation'
					paper_address.text = paper.address
				end
			end

			paper_genre_type = paper_mods.add_element 'genre'
			if (paper.anthology_id[0] == "W")
				paper_genre_type.text = "workshop publication"
			elsif (paper.anthology_id[0] == "Q" || paper.anthology_id[0] == "J") 
				paper_genre_type.text = "article"
			else
				paper_genre_type.text = "conference publication"
			end

			paper_related_item = paper_mods.add_element 'relatedItem'

			paper_related_item.attributes["type"]="host"
			volume_info = paper_related_item.add_element 'titleInfo'
			volume_name = volume_info.add_element 'title'
			volume_name.text = volume.title
		end
	end

	file = File.new("export/mods/#{volume.anthology_id}.xml",'w')
	file.write xml.to_s
	file.close
end

def export_paper_mods paper
	dash = /[–-]+/
	paper_title = paper.title
	year = paper.year
	volume_title = paper.volume.title
	authors = paper.people
	id = paper.anthology_id
	url = paper.url
	xml = REXML::Document.new "<?xml version='1.0'?>"
	mods=xml.add_element 'mods', {"version" => Time.now}
	mods.attributes["ID"]=id
	title_info = mods.add_element 'titleInfo'
	title_name = title_info.add_element 'title'
	title_name.text = paper_title
	authors.each { |author|
		name = mods.add_element 'name'
		name.attributes["type"]="personal"

		name_part_first = name.add_element 'namePart'
		name_part_first.attributes["type"]="given"
		name_part_first.text = author.first_name

		name_part_last = name.add_element 'namePart'
		name_part_last.attributes["type"]="family"
		name_part_last.text = author.last_name

		role = name.add_element 'role'
		roleterm = role.add_element 'roleTerm'
		roleterm.attributes["authority"]="marcrelator"
		roleterm.attributes["type"]="text"
		roleterm.text="author"

	}

	if (paper.doi) 
	   	identifier = mods.add_element 'identifier'
		identifier.attributes["type"] = "DOI"
		identifier.text = paper.doi
	end

	if (paper.pages)
		part = mods.add_element 'part'
		extent = part.add_element 'extent'
		extent.attributes['unit'] = 'pages'
		startPage = extent.add_element 'start'
		startPage.text = paper.pages.split(dash)[0]
		endPage = extent.add_element 'end'
		endPage.text = paper.pages.split(dash)[1]
	end

	origin_info = mods.add_element 'originInfo'
	date_issued = origin_info.add_element 'dateIssued'
	if paper.publisher
		paper_publisher = origin_info.add_element 'publisher'
		paper_publisher.text = paper.publisher
	end
	date_issued.text = year

	if paper.address or paper.url
		paper_location = mods.add_element 'location'
		if paper.url
			paper_url = paper_location.add_element 'url'
			paper_url.text = url
		end
		if paper.address
			paper_address = paper_location.add_element 'physicalLocation'
			paper_address.text = paper.address
		end
	end

	related_item = mods.add_element 'relatedItem'
	related_item.attributes["type"]="host"

	genre_type = related_item.add_element 'genre'
	volume_info = related_item.add_element 'titleInfo'
	volume_name = volume_info.add_element 'title'
        volume_name.text = volume_title # as default
	if( paper.anthology_id[0] == "W")
		genre_type.text = "workshop publication"
	elsif (paper.anthology_id[0] == "Q" || paper.anthology_id[0] == "J") 
		genre_type.text = "academic journal"
                if (paper.volume.journal_volume)
                  if (!part)
                    part = mods.add_element 'part'
                  end
                  part_detail_volume = part.add_element 'detail'
                  part_detail_volume.attributes['type'] = 'volume'
                  part_detail_volume_number = part_detail_volume.add_element 'number'
                  part_detail_volume_number.text = paper.volume.journal_volume
                end
                if (paper.volume.journal_issue)
                  if (!part)
                    part = mods.add_element 'part'
                  end
                  part_detail_issue = part.add_element 'detail'
                  part_detail_issue.attributes['type'] = 'issue'
                  part_detail_issue_number = part_detail_issue.add_element 'number'
                  part_detail_issue_number.text = paper.volume.journal_issue
                end
                if (paper.volume.journal_title)
	          volume_name.text = paper.volume.journal_title
                end
	else
		genre_type.text = "conference publication"
	end

	file = File.new("export/mods/#{paper.anthology_id}.xml",'w')
	file.write xml.to_s
	file.close			
end


namespace :export do
	desc "Export paper mods xml"
	task :paper_modsxml, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "Exporting modsxml for paper #{paper.anthology_id}"
				export_paper_mods paper
			end
		else
			puts "Exporting modsxml for paper #{args[:anthology_id]}"
			export_paper_mods Paper.find_by_anthology_id(args[:anthology_id])
		end
	end

	desc "Export paper bib"
	task :paper_bib, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			all = Paper.all.count
			i = 0
			Paper.all.each do |paper|
				i += 1
				if i % 100 == 0
			       	        puts "#{i}/#{all} Exporting bib for paper #{paper.anthology_id}"
				end
				run_cmd_quietly "xml2bib -nb -w export/mods/#{paper.anthology_id}.xml 2>&1 >export/bib/#{paper.anthology_id}.bib"
			end
		else
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			run_cmd_quietly "xml2bib -nb -w export/mods/#{paper.anthology_id}.xml 2>&1 >export/bib/#{paper.anthology_id}.bib"
		end
	end

	desc "Export paper bib into single file"
	task :paper_bib_single => :environment do |t, args|
		all = Paper.all.count
		i = 0
		`rm -f export/bib/anthology.bib`
		Paper.all.sort { |a,b| a.anthology_id <=> b.anthology_id }.each do |paper|
			i += 1
			if i % 100 == 0
			       puts "#{i}/#{all} Exporting bib for paper #{paper.anthology_id}"
                        end
			run_cmd_quietly "xml2bib -nb -w export/mods/#{paper.anthology_id}.xml 2>&1 >>export/bib/anthology.bib"
		end
	end

	desc "Export paper ris"
	task :paper_ris, [:anthology_id]=> :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "Exporting ris for paper #{paper.anthology_id}"
				`xml2ris export/mods/#{paper.anthology_id}.xml >export/ris/#{paper.anthology_id}.ris`
			end
		else
			puts "Exporting ris for paper #{args[:anthology_id]}"
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`xml2ris export/mods/#{paper.anthology_id}.xml >export/ris/#{paper.anthology_id}.ris`
		end
	end

	desc "Export paper endf"
	task :paper_endf, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "Exporting endf for paper #{paper.anthology_id}"
				`xml2end export/mods/#{paper.anthology_id}.xml >export/endf/#{paper.anthology_id}.endf`
			end
		else
			puts "Exporting endf for paper #{args[:anthology_id]}"
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`xml2end export/mods/#{paper.anthology_id}.xml >export/endf/#{paper.anthology_id}.endf`
		end
	end


	desc "Export paper word"
	task :paper_word, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "Exporting word for paper #{paper.anthology_id}"
				`xml2wordbib export/mods/#{paper.anthology_id}.xml >export/word/#{paper.anthology_id}.word`
			end
		else
			puts "Exporting word for paper #{args[:anthology_id]}"
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`xml2wordbib export/mods/#{paper.anthology_id}.xml >export/word/#{paper.anthology_id}.word`
		end
	end


	desc "Export paper DBLP"
	task :paper_dblp, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Paper.all.each do |paper|
				puts "Exporting DBLP for paper #{paper.anthology_id}"
				`ruby lib/bibscript/xml2dblp.rb export/mods/#{paper.anthology_id}.xml >export/dblp/#{paper.anthology_id}.html`
			end
		else
			puts "Exporting DBLP for paper #{args[:anthology_id]}"
			paper = Paper.find_by_anthology_id(args[:anthology_id])
			`ruby lib/bibscript/xml2dblp.rb export/mods/#{paper.anthology_id}.xml >export/dblp/#{paper.anthology_id}.html`
		end
	end


	desc "Export volume mods xml"
	task :volume_modsxml, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "Exporting modsxml for volume #{volume.anthology_id}"
				export_volume_mods volume
			end
		else
			puts "Exporting modsxml for volume #{args[:anthology_id]}"
			export_volume_mods Volume.find_by_anthology_id(args[:anthology_id])
		end
	end

	desc "Export volume bib"
	task :volume_bib, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "Exporting bib for volume #{volume.anthology_id}"
				`xml2bib export/mods/#{volume.anthology_id}.xml >export/bib/#{volume.anthology_id}.bib`
			end
		else
			puts "Exporting bib for volume #{args[:anthology_id]}"
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2bib export/mods/#{volume.anthology_id}.xml >export/bib/#{volume.anthology_id}.bib`
		end
	end

	desc "Export volume ris"
	task :volume_ris, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "Exporting ris for volume #{volume.anthology_id}"
				`xml2ris export/mods/#{volume.anthology_id}.xml >export/ris/#{volume.anthology_id}.ris`
			end
		else
			puts "Exporting ris for volume #{args[:anthology_id]}"
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2ris export/mods/#{volume.anthology_id}.xml >export/ris/#{volume.anthology_id}.ris`
		end
	end

	desc "Export volume endf"
	task :volume_endf, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "Exporting endf for volume #{volume.anthology_id}"
				`xml2end export/mods/#{volume.anthology_id}.xml >export/endf/#{volume.anthology_id}.endf`
			end
		else
			puts "Exporting endf for volume #{args[:anthology_id]}"
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2end export/mods/#{volume.anthology_id}.xml >export/endf/#{volume.anthology_id}.endf`
		end
	end

	desc "Export volume word"
	task :volume_word, [:anthology_id]=> :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "Exporting word for volume #{volume.anthology_id}"
				`xml2wordbib export/mods/#{volume.anthology_id}.xml >export/word/#{volume.anthology_id}.word`
			end
		else
			puts "Exporting word for volume #{args[:anthology_id]}"
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`xml2wordbib export/mods/#{volume.anthology_id}.xml >export/word/#{volume.anthology_id}.word`
		end
	end

	desc "Export volume DBLP"
	task :volume_dblp, [:anthology_id] => :environment do |t, args|
		if not args[:anthology_id]
			Volume.all.each do |volume|
				puts "Exporting DBLP for volume #{volume.anthology_id}"
				`ruby lib/bibscript/xml2dblp.rb export/mods/#{volume.anthology_id}.xml >export/dblp/#{volume.anthology_id}.xml`
			end
		else
			puts "Exporting DBLP for volume #{args[:anthology_id]}"
			volume = Volume.find_by_anthology_id(args[:anthology_id])
			`ruby lib/bibscript/xml2dblp.rb export/mods/#{volume.anthology_id}.xml >export/dblp/#{volume.anthology_id}.xml`
		end
	end

	# desc "Export volume acm"
	# task :export_volume_acm, [:anthology_id] => :environment do |t, args|
	# 	if not args[:anthology_id]
	# 		Volume.all.each do |volume|
	# 			puts "Exporting acm volume #{volume.anthology_id}"
	# 			`ruby lib/bibscript/mods2acm.rb export/mods/#{volume.anthology_id}.xml >export/csv/#{volume.anthology_id}.csv`
	# 		end
	# 	else
	# 		volume = Volume.find_by_anthology_id(args[:anthology_id])
	# 		`ruby lib/bibscript/xml2dblp.rb export/mods/#{volume.anthology_id}.xml >export/dblp/#{volume.anthology_id}.html`
	# 	end
	# end

	desc "Export paper mods xml"
	task :antho_bib => :environment do
	    Volume.all.each do |volume|
                puts "Exporting bib for volume #{volume.anthology_id}"
       	        `xml2bib export/mods{volume.anthology_id}.xml >> export/bib/antho.bib`
            end
        end
end
