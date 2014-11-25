module PapersHelper
    def volume_title(anthology_id)
        if anthology_id[0] == 'W'
            Volume.find_by_anthology_id(@paper.anthology_id[0..5]).title
        else
            Volume.find_by_anthology_id(@paper.anthology_id[0..4]).title
        end
    end

    def journal_title(anthology_id)
        if anthology_id[0] == 'J'
            "Computational Linguistics"
        elsif anthology_id[0] == 'Q'
            "Transactions of the Association of Computational Linguistics"
        else
            volume_title(anthology_id)
        end
    end

    def citation_volume_from_title(title)
        title_no_space = title.gsub(" ", "")
        match_data = title_no_space.match(/Volume(?<volume>\d+)/)
        return match_data && match_data[:volume]
    end

    def citation_issue_from_title(title)
        title_no_space = title.gsub(" ", "")
        match_data = title_no_space.match(/Number(?<volume>\d-\d)|Number(?<volume>\d)|Issue(?<volume>\d)/)
        return match_data && match_data[:volume]
    end
end
