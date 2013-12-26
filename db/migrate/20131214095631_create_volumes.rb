class CreateVolumes < ActiveRecord::Migration
  def change
    create_table :volumes do |t|
      t.string :anthology_id
      t.string :title
      t.string :month
      t.integer :year
      t.string :address
      t.string :publisher
      t.string :url
      t.string :bibtype
      t.string :bibkey
      t.integer :sig_id

      t.timestamps
    end
  end
end
