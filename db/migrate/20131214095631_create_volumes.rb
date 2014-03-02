class CreateVolumes < ActiveRecord::Migration
  def change
    create_table :volumes do |t|
      t.string :anthology_id
      t.string :acronym
      t.string :title
      t.string :month
      t.integer :year
      t.string :address
      t.string :publisher
      t.string :url
      t.string :bibtype
      t.string :bibkey

      t.timestamps
    end

    add_column :volumes, :slug, :string
    add_index :volumes, :slug, unique: true
  end
end
