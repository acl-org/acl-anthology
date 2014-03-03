class CreatePapers < ActiveRecord::Migration
  def change
    create_table :papers do |t|
      t.integer :volume_id
      t.string :anthology_id
      t.text :title
      t.string :month
      t.integer :year
      t.string :address
      t.string :publisher
      t.string :pages
      t.string :url
      t.string :bibtype
      t.string :bibkey
      t.string :attachment
      t.string :attach_type

      t.timestamps
    end

    add_column :papers, :slug, :text
    add_index :papers, :slug, unique: true
  end
end
