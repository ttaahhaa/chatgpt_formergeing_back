### You can run it as follows
# powershell ./git-task.ps1 start feature/my-task
# powershell ./git-task.ps1 finish "Finished my task"

param (
    [string]$action,  # 'start' or 'finish'
    [string]$arg      # branch name or commit message
)

# Start a new branch from main
if ($action -eq "start") {
    git checkout main
    git pull origin main
    git checkout -b $arg
}
# Finish task: commit and push current branch
elseif ($action -eq "finish") {
    $branch = git rev-parse --abbrev-ref HEAD
    git add .
    git commit -m $arg
    git push -u origin $branch
}
# Show usage instructions
else {
    Write-Host "Usage: ./git-task.ps1 start <branch-name> OR finish <commit-message>"
}
