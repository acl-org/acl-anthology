class SigsVolumes < ActiveRecord::Migration
  def change
  	create_table :sigs_volumes, :id => false do |t|
    	t.integer :sig_id
    	t.integer :volume_id
  	end
  end
end
