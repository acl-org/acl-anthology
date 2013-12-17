class CreatePapers < ActiveRecord::Migration
  def change
    create_table :papers do |t|
      t.integer :volume_id
      t.string :anthology_id
      t.string :paper_id
      t.string :title
      t.string :month
      t.integer :year
      t.string :address
      t.string :publisher
      t.string :pages
      t.string :url
      t.string :bibtype
      t.string :bibkey

      t.timestamps
    end
  end
end
