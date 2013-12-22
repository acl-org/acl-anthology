module BlacklightHelper
  include Blacklight::BlacklightHelperBehavior

  def application_name
    "Bestest University Search"
  end

  def author_helper_method args
  	puts args
  	args[:document][:first_name]
  end
end