"""
JSON output writer for indexing results.
"""
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger()


class OutputWriter:
    """Handles writing indexing results to JSON files."""
    
    def __init__(self, output_file: str = "indexing_results.json"):
        """
        Initialize output writer.
        
        Args:
            output_file: Path to output JSON file
        """
        self.output_file = Path(output_file)
    
    def write_results(
        self,
        results: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Write indexing results to JSON file.
        
        Args:
            results: Dictionary containing indexing results
            metadata: Optional metadata to include
            
        Returns:
            True if successful
        """
        try:
            # Prepare output structure
            output_data = self._prepare_output(results, metadata)
            
            # Ensure parent directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results written to {self.output_file}")
            logger.info(f"File size: {self.output_file.stat().st_size} bytes")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to write results: {str(e)}")
            return False
    
    def _prepare_output(
        self,
        results: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Prepare output data structure.
        
        Args:
            results: Indexing results
            metadata: Optional metadata
            
        Returns:
            Formatted output dictionary
        """
        # Calculate statistics
        successful = results.get('successful', [])
        failed = results.get('failed', [])
        already_indexed = results.get('already_indexed', [])
        skipped = results.get('skipped', [])
        
        # Prepare metadata
        output_metadata = {
            'timestamp': datetime.now().isoformat(),
            'total_repositories_processed': len(set(
                r.get('repository', '') for r in 
                successful + failed + already_indexed
            )),
            'total_branches_indexed': len(successful),
            'successful_indexations': len(successful),
            'failed_indexations': len(failed),
            'already_indexed': len(already_indexed),
            'skipped': len(skipped)
        }
        
        # Add custom metadata if provided
        if metadata:
            output_metadata.update(metadata)
        
        # Prepare output structure
        output = {
            'metadata': output_metadata,
            'results': {
                'successful': successful,
                'failed': failed,
                'already_indexed': already_indexed,
                'skipped': skipped
            }
        }
        
        return output
    
    def append_result(self, result: Dict[str, Any]) -> bool:
        """
        Append a single result to existing output file.
        
        Args:
            result: Result dictionary to append
            
        Returns:
            True if successful
        """
        try:
            # Load existing data
            if self.output_file.exists():
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    'metadata': {},
                    'results': {
                        'successful': [],
                        'failed': [],
                        'already_indexed': [],
                        'skipped': []
                    }
                }
            
            # Append result to appropriate category
            status = result.get('status', 'failed')
            if status == 'success':
                data['results']['successful'].append(result)
            elif status == 'already_indexed':
                data['results']['already_indexed'].append(result)
            elif status == 'skipped':
                data['results']['skipped'].append(result)
            else:
                data['results']['failed'].append(result)
            
            # Update metadata
            data['metadata']['last_updated'] = datetime.now().isoformat()
            
            # Write back
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to append result: {str(e)}")
            return False
    
    def read_results(self) -> Dict[str, Any]:
        """
        Read results from output file.
        
        Returns:
            Dictionary with results or empty dict if file doesn't exist
        """
        try:
            if not self.output_file.exists():
                logger.warning(f"Output file does not exist: {self.output_file}")
                return {}
            
            with open(self.output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Read results from {self.output_file}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to read results: {str(e)}")
            return {}
    
    def get_summary(self) -> str:
        """
        Get a text summary of the results.
        
        Returns:
            Formatted summary string
        """
        try:
            data = self.read_results()
            
            if not data:
                return "No results available"
            
            metadata = data.get('metadata', {})
            results = data.get('results', {})
            
            summary = [
                "=" * 60,
                "INDEXING RESULTS SUMMARY",
                "=" * 60,
                f"Timestamp: {metadata.get('timestamp', 'N/A')}",
                f"Search Term: {metadata.get('search_term', 'N/A')}",
                "",
                "Statistics:",
                f"  Total Repositories: {metadata.get('total_repositories_processed', 0)}",
                f"  Branches Indexed: {metadata.get('total_branches_indexed', 0)}",
                f"  Successful: {metadata.get('successful_indexations', 0)}",
                f"  Failed: {metadata.get('failed_indexations', 0)}",
                f"  Already Indexed: {metadata.get('already_indexed', 0)}",
                f"  Skipped: {metadata.get('skipped', 0)}",
                "",
            ]
            
            # Add execution time if available
            if 'execution_time_seconds' in metadata:
                summary.append(f"Execution Time: {metadata['execution_time_seconds']:.2f} seconds")
            
            summary.append("=" * 60)
            
            return "\n".join(summary)
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            return "Error generating summary"
    
    def export_csv(self, csv_file: str = None) -> bool:
        """
        Export results to CSV format.
        
        Args:
            csv_file: Path to CSV file (optional, defaults to output_file with .csv extension)
            
        Returns:
            True if successful
        """
        try:
            import csv
            
            if csv_file is None:
                csv_file = self.output_file.with_suffix('.csv')
            
            data = self.read_results()
            if not data:
                logger.warning("No data to export")
                return False
            
            results = data.get('results', {})
            all_results = (
                results.get('successful', []) +
                results.get('failed', []) +
                results.get('already_indexed', [])
            )
            
            if not all_results:
                logger.warning("No results to export")
                return False
            
            # Write CSV
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['repository', 'branch', 'status', 'message', 'timestamp']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in all_results:
                    writer.writerow({
                        'repository': result.get('repository', ''),
                        'branch': result.get('branch', ''),
                        'status': result.get('status', ''),
                        'message': result.get('message', result.get('error', '')),
                        'timestamp': result.get('timestamp', '')
                    })
            
            logger.info(f"Results exported to CSV: {csv_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export CSV: {str(e)}")
            return False


def format_results_table(results: List[Dict[str, Any]]) -> str:
    """
    Format results as a text table.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        Formatted table string
    """
    if not results:
        return "No results to display"
    
    # Calculate column widths
    max_repo = max(len(r.get('repository', '')) for r in results)
    max_branch = max(len(r.get('branch', '')) for r in results)
    max_status = max(len(r.get('status', '')) for r in results)
    
    # Ensure minimum widths
    max_repo = max(max_repo, 20)
    max_branch = max(max_branch, 10)
    max_status = max(max_status, 10)
    
    # Build table
    lines = []
    header = f"{'Repository':<{max_repo}} | {'Branch':<{max_branch}} | {'Status':<{max_status}}"
    lines.append(header)
    lines.append("-" * len(header))
    
    for result in results:
        repo = result.get('repository', '')[:max_repo]
        branch = result.get('branch', '')[:max_branch]
        status = result.get('status', '')[:max_status]
        lines.append(f"{repo:<{max_repo}} | {branch:<{max_branch}} | {status:<{max_status}}")
    
    return "\n".join(lines)

# Made with Bob
