module BlacklightHelper
  include Blacklight::BlacklightHelperBehavior

  def application_name
    "ACL anthropoplogy"
  end

  def author_helper_method args
  	puts args
  	args[:document][:first_name]
  end
end