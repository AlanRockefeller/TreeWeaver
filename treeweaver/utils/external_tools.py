# This module will provide an interface for interacting with external command-line tools.

import subprocess
import os
import shutil
import tempfile
import logging
import re # For parsing output
from typing import List, Tuple, Optional

from treeweaver.config import settings_manager

logger = logging.getLogger(__name__)

def _check_tool_path(tool_key: str) -> Optional[str]:
    """
    Retrieves and validates the path for a given tool from settings.
    Checks if the path is set, exists, and is executable.
    Also checks if the command is in PATH if no full path is given.
    """
    tool_path = settings_manager.get_setting(f"external_tool_paths.{tool_key}")
    if not tool_path:
        logger.error(f"{tool_key.upper()} path is not configured in settings.")
        return None

    if os.path.isabs(tool_path) or os.path.exists(tool_path): # Checks if path string itself points to something
        if not os.path.isfile(tool_path):
            logger.error(f"{tool_key.upper()} path '{tool_path}' is not a file.")
            return None
        if not os.access(tool_path, os.X_OK):
            logger.error(f"{tool_key.upper()} file '{tool_path}' is not executable.")
            return None
        return tool_path # Verified path
    else:
        found_path = shutil.which(tool_path)
        if found_path:
            logger.debug(f"Found {tool_key.upper()} in PATH: {found_path}")
            return found_path # Return the full path found by shutil.which
        else:
            logger.error(f"{tool_key.upper()} command '{tool_path}' not found in system PATH and not a valid direct path.")
            return None

def _run_command(command: List[str], cwd: Optional[str] = None, timeout_seconds: int = 3600) -> Tuple[bool, str, str]:
    """
    Executes a command using subprocess. Returns (success, stdout, stderr).
    """
    if not command or not command[0]:
        logger.error("Invalid command provided to _run_command.")
        return False, "", "Invalid command"
    try:
        command = [str(c) for c in command]
        cmd_str_for_log = ' '.join(command)
        logger.info(f"Running command: {cmd_str_for_log} {('in ' + cwd) if cwd else ''}")
        process = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout_seconds
        )
        if process.stdout: logger.debug(f"Command STDOUT:\n{process.stdout.strip()}")
        # Always log stderr for debugging, even on success, as some tools put info there
        if process.stderr: logger.debug(f"Command STDERR:\n{process.stderr.strip()}")

        if process.returncode == 0:
            logger.info(f"Command executed successfully: {cmd_str_for_log}")
            return True, process.stdout, process.stderr
        else:
            logger.error(f"Command failed with return code {process.returncode}: {cmd_str_for_log}")
            # More prominent logging of stderr if it's the primary error output
            if process.stderr.strip():
                 logger.error(f"Tool STDERR for failed command:\n{process.stderr.strip()}")
            return False, process.stdout, process.stderr
    except FileNotFoundError:
        logger.error(f"Command not found: {command[0]}. Ensure it's installed and in PATH or configured correctly.")
        return False, "", f"Command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout_seconds} seconds: {' '.join(command)}")
        return False, "", f"Command timed out after {timeout_seconds} seconds."
    except Exception as e:
        logger.error(f"An unexpected error occurred while running command {' '.join(command)}: {e}", exc_info=True)
        return False, "", f"Unexpected error: {str(e)}"

def run_mafft(input_fasta_path: str, output_fasta_path: str, num_threads: int = 1, options: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    mafft_path = _check_tool_path("mafft")
    if not mafft_path: return False, "MAFFT executable not found or not configured. Please check settings."
    if not os.path.exists(input_fasta_path):
        logger.error(f"MAFFT input file not found: {input_fasta_path}")
        return False, f"Input FASTA file not found: {input_fasta_path}"

    command = [mafft_path, "--thread", str(num_threads), "--auto"]
    if options: command.extend(options)
    command.append(input_fasta_path)

    logger.info(f"Running MAFFT: input='{input_fasta_path}', output='{output_fasta_path}'")
    success, stdout_data, stderr_data = _run_command(command)

    if success and stdout_data:
        try:
            with open(output_fasta_path, "w") as f: f.write(stdout_data)
            logger.info(f"MAFFT alignment saved to {output_fasta_path}")
            if os.path.getsize(output_fasta_path) > 0: return True, None # Success, no error message
            else:
                err_msg = "MAFFT produced an empty output file."
                if stderr_data.strip(): err_msg += f" STDERR: {stderr_data.strip()[:100]}"
                logger.error(err_msg)
                return False, err_msg
        except IOError as e:
            logger.error(f"Failed to write MAFFT output to {output_fasta_path}: {e}")
            return False, f"Failed to write MAFFT output: {e}"
    elif success and not stdout_data: # Success but no output
        err_msg = "MAFFT ran successfully but produced no output (stdout was empty)."
        if stderr_data.strip(): err_msg += f" STDERR: {stderr_data.strip()[:100]}"
        logger.error(err_msg)
        return False, err_msg
    else: # Tool execution failed
        return False, f"MAFFT execution failed. Error: {stderr_data.strip()[:200] if stderr_data.strip() else 'Unknown error'}"

def run_raxml_ng(alignment_phylip_path: str, model: str, prefix: str,
                 working_dir: Optional[str] = None, seed: int = 12345, threads: int = 1,
                 bootstrap_replicates: int = 0) -> Tuple[bool, Optional[str]]:
    raxml_ng_path = _check_tool_path("raxmlng")
    if not raxml_ng_path: return False, "RAxML-NG executable not found or not configured."
    if not os.path.exists(alignment_phylip_path):
        return False, f"RAxML-NG input alignment file not found: {alignment_phylip_path}"

    temp_dir_obj = None
    actual_working_dir = working_dir
    if not actual_working_dir:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="raxml_")
        actual_working_dir = temp_dir_obj.name
        logger.info(f"Using temporary directory for RAxML-NG: {actual_working_dir}")
    elif not os.path.isdir(actual_working_dir):
        try: os.makedirs(actual_working_dir, exist_ok=True)
        except OSError as e: return False, f"Cannot create RAxML-NG working directory '{actual_working_dir}': {e}"

    msa_abs_path = os.path.abspath(alignment_phylip_path)
    # RAxML-NG --prefix is an output prefix, not a directory. Files are created in CWD.
    output_prefix_for_cmd = os.path.basename(prefix)

    command = [
        raxml_ng_path, "--msa", msa_abs_path, "--model", model,
        "--prefix", output_prefix_for_cmd, "--seed", str(seed),
        "--threads", "auto" if threads <=0 else str(threads), "--force",
    ]
    if bootstrap_replicates > 0: command.extend(["--bs-reps", str(bootstrap_replicates)])

    logger.info(f"Running RAxML-NG in {actual_working_dir} with prefix {output_prefix_for_cmd}")
    success, stdout, stderr = _run_command(command, cwd=actual_working_dir)

    # Expected output file, relative to the CWD of the tool
    best_tree_filename = output_prefix_for_cmd + ".raxml.bestTree"
    best_tree_path_in_cwd = os.path.join(actual_working_dir, best_tree_filename)

    # If bootstraps were run, a support tree might be more relevant, e.g., prefix + ".raxml.support"
    # This depends on the RAxML-NG commands used (e.g. if --support was added after a bootstrap run)
    # For now, assume .bestTree is the primary target.

    if not success:
        err_summary = stderr.strip()[:200] if stderr.strip() else "Unknown error."
        if temp_dir_obj: temp_dir_obj.cleanup()
        return False, f"RAxML-NG execution failed. Error: {err_summary}"

    final_tree_path = None
    if os.path.exists(best_tree_path_in_cwd):
        logger.info(f"RAxML-NG completed. Best tree: {best_tree_path_in_cwd}")
        final_tree_path = best_tree_path_in_cwd
        if temp_dir_obj: # If using temp dir, copy the primary result to a stable location
            stable_output_dir = os.path.dirname(prefix) if os.path.dirname(prefix) else os.getcwd()
            os.makedirs(stable_output_dir, exist_ok=True)
            copied_tree_path = os.path.join(stable_output_dir, best_tree_filename)
            try:
                shutil.copy2(best_tree_path_in_cwd, copied_tree_path)
                logger.info(f"Copied RAxML-NG best tree to {copied_tree_path}")
                final_tree_path = copied_tree_path
            except Exception as e_copy:
                logger.error(f"Error copying RAxML-NG results from temp dir: {e_copy}")
                # Return the temp path, but it's about to be deleted which is problematic.
                # Better to signal this as a failure if copy is essential.
                if temp_dir_obj: temp_dir_obj.cleanup()
                return False, f"RAxML-NG ran but failed to copy tree from temp storage: {e_copy}"
    else:
        err_msg = f"RAxML-NG ran but best tree file not found at {best_tree_path_in_cwd}."
        if stderr.strip(): err_msg += f" STDERR: {stderr.strip()[:100]}"
        logger.error(err_msg)
        if temp_dir_obj: temp_dir_obj.cleanup()
        return False, err_msg

    if temp_dir_obj: temp_dir_obj.cleanup()
    return True, final_tree_path


def parse_iqtree_model_finder_output(iqtree_report_file: str) -> Optional[str]:
    if not os.path.exists(iqtree_report_file):
        logger.error(f"IQ-TREE report file not found for parsing: {iqtree_report_file}")
        return None
    try:
        with open(iqtree_report_file, 'r', encoding='utf-8') as f: content = f.read()
        bic_match = re.search(r"Best-fit model according to BIC:\s*([A-Za-z0-9+/*{}\-.@]+)", content)
        if bic_match: model = bic_match.group(1).strip(); logger.info(f"IQ-TREE best model (BIC): {model}"); return model
        aic_match = re.search(r"Best-fit model according to AIC:\s*([A-Za-z0-9+/*{}\-.@]+)", content)
        if aic_match: model = aic_match.group(1).strip(); logger.info(f"IQ-TREE best model (AIC): {model}"); return model
        logger.warning(f"Best-fit model not found (BIC/AIC) in IQ-TREE report: {iqtree_report_file}")
    except IOError as e: logger.error(f"IOError parsing IQ-TREE report {iqtree_report_file}: {e}")
    except Exception as e: logger.error(f"Unexpected error parsing IQ-TREE report {iqtree_report_file}: {e}", exc_info=True)
    return None

def parse_modeltest_ng_output(modeltest_ng_report_file: str) -> Optional[str]:
    if not os.path.exists(modeltest_ng_report_file):
        logger.error(f"ModelTest-NG report file not found for parsing: {modeltest_ng_report_file}")
        return None
    try:
        with open(modeltest_ng_report_file, 'r', encoding='utf-8') as f: content = f.read()
        bic_model_match = re.search(r"(?:Best model by BIC selection criterion|BIC\s*:\s*)\s*([A-Za-z0-9+/*{}\-.@]+)", content)
        if bic_model_match:
            model = bic_model_match.group(1).strip()
            logger.info(f"ModelTest-NG best model (BIC): {model}")
            return model
        logger.warning(f"Best-fit model (BIC) not found in ModelTest-NG report: {modeltest_ng_report_file}")
    except IOError as e: logger.error(f"IOError parsing ModelTest-NG report {modeltest_ng_report_file}: {e}")
    except Exception as e: logger.error(f"Unexpected error parsing ModelTest-NG report {modeltest_ng_report_file}: {e}", exc_info=True)
    return None

def run_iqtree(alignment_path: str, prefix: str, working_dir: Optional[str] = None,
               sequence_type: Optional[str] = None, model: Optional[str] = "MFP",
               bootstrap_replicates: int = 0, threads: int = 1,
               run_model_finder_only: bool = False) -> Tuple[bool, Optional[str]]:
    iqtree_path = _check_tool_path("iqtree")
    if not iqtree_path: return False, "IQ-TREE executable not found or not configured."
    if not os.path.exists(alignment_path): return False, f"Input alignment file not found: {alignment_path}"

    temp_dir_obj = None; actual_working_dir = working_dir
    if not actual_working_dir: temp_dir_obj = tempfile.TemporaryDirectory(prefix="iqtree_"); actual_working_dir = temp_dir_obj.name
    elif not os.path.isdir(actual_working_dir):
        try: os.makedirs(actual_working_dir, exist_ok=True)
        except OSError as e: return False, f"Cannot create IQ-TREE working directory: {e}"

    msa_abs_path = os.path.abspath(alignment_path)
    output_prefix_for_cmd = os.path.basename(prefix)
    command = [iqtree_path, "-s", msa_abs_path, "--prefix", output_prefix_for_cmd, "-T", str(threads) if threads > 0 else "AUTO", "-redo"]
    if sequence_type: command.extend(["-st", sequence_type])
    current_model_arg = model
    if run_model_finder_only: current_model_arg = "MFP"
    if current_model_arg: command.extend(["-m", current_model_arg])
    if bootstrap_replicates > 0 and not run_model_finder_only: command.extend(["-b", str(bootstrap_replicates)])

    success, stdout, stderr = _run_command(command, cwd=actual_working_dir)
    if not success:
        err_summary = stderr.strip()[:200] if stderr.strip() else "Unknown error."
        if temp_dir_obj: temp_dir_obj.cleanup()
        return False, f"IQ-TREE execution failed. Error: {err_summary}"

    effective_output_prefix = os.path.join(actual_working_dir, output_prefix_for_cmd)
    report_file = effective_output_prefix + ".iqtree"; tree_file = effective_output_prefix + ".treefile"
    result_data = None; is_file_path_result = False

    if run_model_finder_only or "MFP" in (current_model_arg or "").upper():
        if os.path.exists(report_file):
            result_data = parse_iqtree_model_finder_output(report_file)
            if not result_data: result_data = report_file; is_file_path_result = True; logger.error(f"IQ-TREE output parsing failed for {report_file}")
        else: return False, f"IQ-TREE report file not found: {os.path.basename(report_file)}"
    elif os.path.exists(tree_file): result_data = tree_file; is_file_path_result = True
    elif os.path.exists(report_file): result_data = report_file; is_file_path_result = True; logger.warning("IQ-TREE treefile not found, using report file.")
    else: return False, "IQ-TREE ran but no expected output found."

    if temp_dir_obj and is_file_path_result and result_data:
        stable_output_dir = os.path.dirname(prefix) if os.path.dirname(prefix) else os.getcwd()
        os.makedirs(stable_output_dir, exist_ok=True)
        copied_path = os.path.join(stable_output_dir, os.path.basename(str(result_data)))
        try: shutil.copy2(str(result_data), copied_path); result_data = copied_path
        except Exception as e: if temp_dir_obj:temp_dir_obj.cleanup(); return False, f"Failed to copy result: {e}"
    if temp_dir_obj: temp_dir_obj.cleanup()

    if not result_data: return False, "IQ-TREE result processing failed."
    if is_file_path_result: # Parsing failed or was not model string
        return False, f"Tool ran but model parsing failed. Report: {os.path.basename(str(result_data))}"
    return True, result_data # Parsed model string

def run_modeltest_ng(alignment_phylip_path: str, output_base_name: str, working_dir: Optional[str] = None,
                     sequence_type: str = "DNA", threads: int = 1) -> Tuple[bool, Optional[str]]:
    modeltest_ng_path = _check_tool_path("modeltest-ng")
    if not modeltest_ng_path: return False, "ModelTest-NG executable not found."
    if not os.path.exists(alignment_phylip_path): return False, f"Input alignment file not found: {alignment_phylip_path}"

    temp_dir_obj = None; actual_working_dir = working_dir
    if not actual_working_dir: temp_dir_obj = tempfile.TemporaryDirectory(prefix="mtng_"); actual_working_dir = temp_dir_obj.name
    elif not os.path.isdir(actual_working_dir):
        try: os.makedirs(actual_working_dir, exist_ok=True)
        except OSError as e: return False, f"Cannot create ModelTest-NG working directory: {e}"

    msa_abs_path = os.path.abspath(alignment_phylip_path)
    output_base_for_cmd = os.path.basename(output_base_name)
    command = [modeltest_ng_path, "-i", msa_abs_path, "-d", sequence_type.lower(), "-p", str(threads), "-o", os.path.join(actual_working_dir, output_base_for_cmd)]

    success, stdout, stderr = _run_command(command, cwd=actual_working_dir)
    if not success:
        err_summary = stderr.strip()[:200] if stderr.strip() else "Unknown error."
        if temp_dir_obj: temp_dir_obj.cleanup()
        return False, f"ModelTest-NG execution failed. Error: {err_summary}"

    report_file = os.path.join(actual_working_dir, output_base_for_cmd + ".out")
    result_data = None; is_file_path_result = False

    if os.path.exists(report_file):
        result_data = parse_modeltest_ng_output(report_file)
        if not result_data: result_data = report_file; is_file_path_result = True; logger.error(f"ModelTest-NG output parsing failed for {report_file}")
    else: return False, f"ModelTest-NG report file not found: {os.path.basename(report_file)}"

    if temp_dir_obj and is_file_path_result and result_data:
        stable_output_dir = os.path.dirname(output_base_name) if os.path.dirname(output_base_name) else os.getcwd()
        os.makedirs(stable_output_dir, exist_ok=True)
        copied_path = os.path.join(stable_output_dir, os.path.basename(str(result_data)))
        try: shutil.copy2(str(result_data), copied_path); result_data = copied_path
        except Exception as e: if temp_dir_obj:temp_dir_obj.cleanup(); return False, f"Failed to copy result: {e}"
    if temp_dir_obj: temp_dir_obj.cleanup()

    if not result_data: return False, "ModelTest-NG result processing failed."
    if is_file_path_result:
        return False, f"Tool ran but model parsing failed. Report: {os.path.basename(str(result_data))}"
    return True, result_data # Parsed model string

# Main block for direct testing (optional)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("External tools module direct test execution (requires tools to be configured and test data).")
    # Add specific test calls here if needed
    pass
