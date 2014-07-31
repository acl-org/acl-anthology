module PapersHelper
	def get_citation_volume_from_title(title)
		title_no_space = title.gsub(" ", "")
		match_data = title_no_space.match(/Volume(?<volume>\d+)/)
		return match_data && match_data[:volume]
	end

	def get_citation_issue_from_title(title)
		title_no_space = title.gsub(" ", "")
		match_data = title_no_space.match(/Number(?<volume>\d-\d)|Number(?<volume>\d)|Issue(?<volume>\d)/)
		return match_data && match_data[:volume]
	end
end
