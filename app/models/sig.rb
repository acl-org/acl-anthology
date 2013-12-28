class Sig < ActiveRecord::Base
	has_many :volumes
  	#validates_associated :volumes
  	accepts_nested_attributes_for :volumes
  	
end
