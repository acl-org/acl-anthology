class PeopleVolumes < ActiveRecord::Migration
  def change
  	create_table :people_volumes, :id => false do |t|
  		t.integer :person_id
    	t.string :volume_id
  	end
  end
end
