class ApplicationController < ActionController::Base
	# Adds a few additional behaviors into the application controller 
	include Blacklight::Controller
	# Please be sure to impelement current_user and user_session. Blacklight depends on 
	# these methods in order to perform user specific actions. 

	layout 'blacklight'

	# Prevent CSRF attacks by raising an exception.
	# For APIs, you may want to use :null_session instead.
	protect_from_forgery with: :exception

  	after_filter :store_location

	def store_location
		# store last url - this is needed for post-login redirect to whatever the user last visited.
		if (request.fullpath != "/users/sign_in" &&
			request.fullpath != "/users/sign_up" &&
			request.fullpath != "/users/password" &&
			# request.fullpath != "/users/sign_out" &&
			!request.xhr?) # don't store ajax calls
		session[:previous_url] = request.fullpath 
	  end
	end

	def after_sign_in_path_for(resource)
	  session[:previous_url] || root_path
	end

	def after_sign_out_path_for(resource_or_scope)
	  	request.referrer
	end
end
