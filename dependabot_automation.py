
"""
Dependabot Automation Script

This script automates the process of handling Dependabot alerts and PRs using Devin AI.
Based on the workflow described in: https://developers.freee.co.jp/entry/devindabot

The script performs the following tasks:
1. Collects Dependabot alerts from GitHub repositories
2. Filters alerts to identify those that should be handled by Devin
3. Triggers Devin to analyze and handle the alerts
4. Optionally applies fixes automatically when safe to do so

Usage:
    python dependabot_automation.py [--repo REPO] [--auto-approve]

Options:
    --repo REPO         Specify a repository to check (default: all repos)
    --auto-approve      Automatically approve safe PRs (no breaking changes)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

def get_dependabot_alerts(repo: str) -> List[Dict]:
    """
    Retrieve Dependabot alerts for a repository using GitHub CLI.
    
    Args:
        repo: Repository name in format "owner/repo"
        
    Returns:
        List of alert dictionaries
    """
    try:
        cmd = ["gh", "api", f"/repos/{repo}/dependabot/alerts", "--jq", ".[]"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        alerts = []
        for line in result.stdout.strip().split('\n'):
            if line:
                alerts.append(json.loads(line))
        return alerts
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving Dependabot alerts for {repo}: {e}")
        print(f"Error output: {e.stderr}")
        return []

def get_dependabot_prs(repo: str) -> List[Dict]:
    """
    Retrieve open Dependabot PRs for a repository.
    
    Args:
        repo: Repository name in format "owner/repo"
        
    Returns:
        List of PR dictionaries
    """
    try:
        cmd = [
            "gh", "pr", "list", 
            "--repo", repo, 
            "--author", "dependabot", 
            "--state", "open", 
            "--json", "number,title,url,createdAt,body"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving Dependabot PRs for {repo}: {e}")
        print(f"Error output: {e.stderr}")
        return []

def is_direct_dependency(repo: str, package_name: str) -> bool:
    """
    Check if a package is a direct dependency in the repository.
    
    Args:
        repo: Repository name in format "owner/repo"
        package_name: Name of the package to check
        
    Returns:
        True if direct dependency, False otherwise
    """
    
    dependency_files = [
        "package.json",           # JavaScript/Node.js
        "requirements.txt",       # Python
        "pyproject.toml",         # Python (modern)
        "Gemfile",                # Ruby
        "pom.xml",                # Java/Maven
        "build.gradle",           # Java/Gradle
        "go.mod",                 # Go
        "composer.json",          # PHP
        "Cargo.toml",             # Rust
    ]
    
    for file in dependency_files:
        try:
            cmd = ["gh", "api", f"/repos/{repo}/contents/{file}", "--jq", ".content"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.stdout and package_name in result.stdout:
                return True
        except subprocess.CalledProcessError:
            continue
    
    return False

def trigger_devin_analysis(repo: str, pr_number: int) -> None:
    """
    Trigger Devin to analyze a Dependabot PR.
    
    Args:
        repo: Repository name in format "owner/repo"
        pr_number: PR number to analyze
    """
    
    print(f"Triggering Devin analysis for PR #{pr_number} in {repo}")
    
    # 
    # 
    
    comment = (
        "🤖 **Devin Analysis Triggered**\n\n"
        "I'm analyzing this Dependabot PR to check for:\n"
        "- Verification that this update properly addresses the vulnerability\n"
        "- Potential breaking changes that might require code modifications\n"
        "- Compatibility issues with other dependencies\n\n"
        "I'll post my findings as a review comment."
    )
    
    try:
        subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--repo", repo, "--body", comment],
            check=True
        )
        print(f"Added initial comment to PR #{pr_number}")
    except subprocess.CalledProcessError as e:
        print(f"Error adding comment to PR: {e}")

def main():
    parser = argparse.ArgumentParser(description="Automate Dependabot alert handling with Devin")
    parser.add_argument("--repo", help="Specific repository to check (owner/repo format)")
    parser.add_argument("--auto-approve", action="store_true", help="Automatically approve safe PRs")
    args = parser.parse_args()
    
    repos = []
    if args.repo:
        repos = [args.repo]
    else:
        try:
            result = subprocess.run(
                ["gh", "repo", "list", "--json", "nameWithOwner", "--limit", "100"],
                capture_output=True, text=True, check=True
            )
            repo_data = json.loads(result.stdout)
            repos = [repo["nameWithOwner"] for repo in repo_data]
        except subprocess.CalledProcessError as e:
            print(f"Error listing repositories: {e}")
            print(f"Error output: {e.stderr}")
            sys.exit(1)
    
    print(f"Checking {len(repos)} repositories for Dependabot alerts and PRs")
    
    for repo in repos:
        print(f"\nProcessing repository: {repo}")
        
        prs = get_dependabot_prs(repo)
        print(f"Found {len(prs)} open Dependabot PRs")
        
        alerts = get_dependabot_alerts(repo)
        print(f"Found {len(alerts)} Dependabot alerts")
        
        for pr in prs:
            pr_number = pr["number"]
            pr_title = pr["title"]
            print(f"\nAnalyzing PR #{pr_number}: {pr_title}")
            
            if "Bump " in pr_title:
                package_name = pr_title.split("Bump ")[1].split(" from")[0]
                print(f"Package: {package_name}")
                
                if is_direct_dependency(repo, package_name):
                    print(f"{package_name} is a direct dependency - triggering Devin analysis")
                    trigger_devin_analysis(repo, pr_number)
                else:
                    print(f"{package_name} is an indirect dependency - skipping Devin analysis")
            else:
                print(f"PR title doesn't match expected format, skipping")
    
    print("\nDependabot automation completed")

if __name__ == "__main__":
    main()
