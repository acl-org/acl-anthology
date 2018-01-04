#encoding: utf-8
require 'zip'
require 'open-uri'

def create_temp_files(volume)
	tempfiles = []
	(0..volume.papers.size).each do |i|
		tempfiles << Tempfile.new(['paper' + i.to_s, '.pdf'], "#{Rails.root}/tmp")
	end
	return tempfiles
end

def exists_paper_pdf?(anthology_id, tempfiles)
	url_string = "http://aclweb.org/anthology/" + anthology_id
    url = URI.parse(url_string) # Parses the string to url
    res = Net::HTTP.get_response(url) # Gets the response from the url
    redirect_url_string = res['location'] # Get the redirect url
    redirect_url = URI.parse(redirect_url_string)

    if anthology_id[0] == 'W'
    	temp_file = File.new(tempfiles[(anthology_id[-2..-1]).to_i].path,'wb')
    else
    	temp_file = File.new(tempfiles[(anthology_id[-3..-1]).to_i].path,'wb')
    end

    Net::HTTP.start(redirect_url.host, redirect_url.port) do |http|
    	req = Net::HTTP::Head.new(redirect_url)
    	if http.request(req)['Content-Type'].start_with? 'application/pdf'
    		temp_file.write Net::HTTP.get_response(redirect_url).body
    		return true
    	end
    end
    # Testing with the redirect url (aka second redirect)
    res2 = Net::HTTP.get_response(redirect_url)
    redirect_url_string2 = res2['location']
    redirect_url2 = URI.parse(redirect_url_string2)
    Net::HTTP.start(redirect_url2.host, redirect_url.port) do |http|
    	req = Net::HTTP::Head.new(redirect_url2)
    	if http.request(req)['Content-Type'].start_with? 'application/pdf'
    		temp_file.write Net::HTTP.get_response(redirect_url2).body
    		return true
    	end
    end
    temp_file.close
    return false
end

def name_files_with_pages?(volume)
	volume.papers.each do |paper|
		if !paper.pages
			if paper.anthology_id[0] == 'W' && paper.anthology_id[-2..-1] != "00"
				return false
			elsif paper.anthology_id[-3..-1] != "000"
				return false
			end
		end
	end
	return true
end

def export_zip(volume)
	zip_name = "export/acm/" + volume.anthology_id + ".zip"
	puts "Exporting ACM(zip) for volume " + @volume.anthology_id + " at location " + zip_name

	tempfiles = create_temp_files(volume)

	Zip::File.open(zip_name, Zip::File::CREATE) do |acm_zip|
		volume.papers.each do |paper|
			if exists_paper_pdf?(paper.anthology_id, tempfiles)
				puts "Found pdf for " + paper.anthology_id + ". Adding to archive..."
				if paper.people[0]
					author_last_name = paper.people[0].last_name
				else
					author_last_name = "ACL"
				end
				if name_files_with_pages?(volume)
					if paper.pages
						paper_name = "p" + paper.pages.split("–")[0] + "-" + author_last_name + ".pdf"
					else
						paper_name = "p0-" + author_last_name + ".pdf"
					end
				else
					if paper.anthology_id[0] == 'W'
						paper_name = "a" + ((paper.anthology_id[-2..-1]).to_i).to_s + "-" + author_last_name + ".pdf"
					else
						paper_name = "a" + ((paper.anthology_id[-3..-1]).to_i).to_s + "-" + author_last_name + ".pdf"
					end
				end
				if paper.anthology_id[0] == 'W'
					acm_zip.add(paper_name, tempfiles[(paper.anthology_id[-2..-1]).to_i])
				else
					acm_zip.add(paper_name, tempfiles[(paper.anthology_id[-3..-1]).to_i])
				end
				
			end
		end
	end

	puts "Finished creating zip for volume " + @volume.anthology_id
end

def export_csv(volume)
	csv_file = File.new("export/acm/" + volume.anthology_id + ".csv",'w')
	puts "Exporting ACM(csv) file for volume " + volume.anthology_id
	volume.papers.each do |paper|
		type = "Full Paper"
		title = "" + paper.title
		authors = ""
		paper.people.each do |author|
			authors += author.full_name + ';'
		end
		authors = "ACL" if authors == ""
		lead_author_email = "acl@aclweb.org" 
		paper_number = paper.anthology_id[-4..-1]
		
		acm_csv_string = '"' + type + '","' + title + '","' + authors + '","' + lead_author_email + '","' + paper_number + '"' + "\n"
		csv_file << acm_csv_string
	end
	csv_file.close
end

namespace :export do
	desc "Export each anthology to acm format, zip file only"
	task :acm_volume_zip, [:anthology_id] => :environment do |t, args|
		if (args[:anthology_id])
			@volume = Volume.find_by_anthology_id(args[:anthology_id])

			if @volume
				export_zip(@volume)
			else
				puts "Volume #{args[:anthology_id]} was not found!"
			end
		else
			Volume.all.each do |volume|
				export_zip(volume)
			end

		end
	end
end

namespace :export do
	desc "Export each anthology to acm format, csv file only"
	task :acm_volume_csv, [:anthology_id] => :environment do |t, args|
		if (args[:anthology_id])
			@volume = Volume.find_by_anthology_id(args[:anthology_id])

			if @volume
				export_csv(@volume)
			else
				puts "Volume #{args[:anthology_id]} was not found!"
			end
		else
			Volume.all.each do |volume|
				export_csv(volume)
			end
		end
	end
end

namespace :export do
	desc "Export each anthology to acm format, the full anthology"
	task :acm_full, [:export_type] => :environment do |t, args|

		codes = ['A', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'W', 'X', 'Y']
		years = ('65'..'99').to_a + ('00'..'18').to_a
		codes.each do |c|
			years.each do |y|
				volume_found = false # by default, the anthology is empty
				if c == 'W' # If we have a workshop, the volume series will have 2 digits
					volume_series = ('01'..'99').to_a
				else # else, only count first digit
					volume_series = ('1'..'9').to_a
				end

				volume_series.each do |v|
					@volume = Volume.find_by_anthology_id(c + y + "-" + v.to_s)

					if @volume && @volume.anthology_id != "J79-1" #########################################################
						if args[:export_type] == "csv"
							export_csv(@volume)
						elsif args[:export_type] == "zip"
							export_zip(@volume)
						else
							export_csv(@volume)
							export_zip(@volume)
						end
					end
				end
			end
		end
	end
end