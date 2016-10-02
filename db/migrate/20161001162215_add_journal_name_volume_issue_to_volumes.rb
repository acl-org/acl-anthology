require_relative '20160911143333_add_volume_issue_to_papers'

class AddJournalNameVolumeIssueToVolumes < ActiveRecord::Migration
  def change
    revert AddVolumeIssueToPapers
    add_column :volumes, :journal_name, :string
    add_column :volumes, :journal_volume, :string
    add_column :volumes, :journal_issue, :string
  end
end
