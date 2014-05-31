module HomeHelper
	include Blacklight::BlacklightHelperBehavior

	def check_new(event)
		return false if event == nil 
		@volumes = event.volumes
		@volumes.each do |volume|
			if (Date.today - volume.created_at.to_date).to_i < 30
				return true
			end
		end
		return false
	end
end
