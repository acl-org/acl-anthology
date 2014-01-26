#encoding: utf-8
require 'zip'
require 'open-uri'

def exists_pdf_at_url?(url_string)
    url = URI.parse(url_string) # Parses the string to url
    res = Net::HTTP.get_response(url) # Gets the response from the url
    redirect_url_string = res['location'] # Get the redirect url
    redirect_url = URI.parse(redirect_url_string)

    temp_file = File.new("export/acm/.temp_file",'wb')

    Net::HTTP.start(redirect_url.host, redirect_url.port) do |http|
    	req = Net::HTTP::Head.new(redirect_url)
    	if http.request(req)['Content-Type'].start_with? 'application/pdf'
    		temp_file.write Net::HTTP.get_response(redirect_url).body
    		puts "1. " + temp_file.size.to_s
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
			return false
		end
	end
	return true
end

def export_zip(volume)
	zip_name = "export/acm/" + volume.anthology_id + ".zip"
	puts "Creating zip for volume " + @volume.anthology_id + " at location " + zip_name

	Zip::File.open(zip_name, Zip::File::CREATE) do |acm_zip|
		volume.papers.each do |paper|
			file_url = "http://aclweb.org/anthology/" + paper.anthology_id
			if exists_pdf_at_url?(file_url)
				puts "Found pdf for " + paper.anthology_id + ". Adding to archive..."
				if name_files_with_pages?(volume)
					paper_name = "p" + paper.pages.split("–")[0] + "-" + paper.people[0].last_name + ".pdf"
				else
					if paper.anthology_id[0] == 'W'
						paper_name = "a" + ((paper.anthology_id[-2..-1]).to_i).to_s + "-" + paper.people[0].last_name + ".pdf"
					else
						paper_name = "a" + ((paper.anthology_id[-3..-1]).to_i).to_s + "-" + paper.people[0].last_name + ".pdf"
					end
				end
				acm_zip.add(paper_name, "export/acm/.temp_file")
			end
		end
	end

	puts "Finished creating zip for volume " + @volume.anthology_id
end

def export_csv(volume)
	csv_file = File.new("export/acm/" + volume.anthology_id + ".csv",'w')
	
	volume.papers.each do |paper|
		type = "Full Paper"
		title = paper.title
		authors = ""
		paper.people.each do |author|
			authors += author.full_name + ';'
		end
		lead_author_email = "kanmy@comp.nus.edu.sg" 
		paper_number = paper.anthology_id[-4..-1]
		

		acm_csv_string = '"' + type + '","' + title + '","' + authors + '","' + lead_author_email + '","' + paper_number + '"' + "\n"
		csv_file << acm_csv_string
	end
	csv_file.close
end

namespace :export do
	desc "Export each anthology to acm format, zip file only"
	task :acm_volume_zip, [:anthology_id] => :environment do |t, args|
		@volume = Volume.find_by_anthology_id(args[:anthology_id])

		export_zip(@volume)
	end
end

namespace :export do
	desc "Export each anthology to acm format, zip file only"
	task :acm_volume_csv, [:anthology_id] => :environment do |t, args|
		@volume = Volume.find_by_anthology_id(args[:anthology_id])

		export_csv(@volume)
	end
end