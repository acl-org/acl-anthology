module BlacklightHelper
  include Blacklight::BlacklightHelperBehavior

  def application_name
    "ACL anthropoplogy"
  end

  def author_helper_method args
  	args[:document][:author].map!.with_index { |author,i|
  		link_to(author, "/people/" + args[:document][:author_id][i])
  	}
  end

  def volume_helper_method args
  	link_to(args[:document][:volume_anthology], "/volumes/" + args[:document][:volume_id])
  end

  def sig_helper_method args
  	args[:document][:sig_iden].map!.with_index { |sig,i|
  		link_to(sig, "/sigs/" + args[:document][:sig_id][i])
  	}
  end

  def venue_helper_method args
  	args[:document][:venue_name].map!.with_index { |venue,i|
  		link_to(venue, "/venues/" + args[:document][:venue_id][i])
  	}
  end

end