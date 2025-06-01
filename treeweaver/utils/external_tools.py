# This module will provide an interface for interacting with external command-line tools.

import subprocess
import os
import shutil
import tempfile
import logging
import re # For parsing output
from typing import List, Tuple, Optional

from treeweaver.config import settings_manager
# SequenceData is imported for type hinting in future, not directly used in this version of wrappers.
# from treeweaver.core import SequenceData

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

    if os.path.isabs(tool_path) or os.path.exists(tool_path):
        if not os.path.isfile(tool_path):
            logger.error(f"{tool_key.upper()} path '{tool_path}' is not a file.")
            return None
        if not os.access(tool_path, os.X_OK):
            logger.error(f"{tool_key.upper()} file '{tool_path}' is not executable.")
            return None
        return tool_path
    else:
        found_path = shutil.which(tool_path)
        if found_path:
            logger.debug(f"Found {tool_key.upper()} in PATH: {found_path}")
            return found_path
        else:
            logger.error(f"{tool_key.upper()} command '{tool_path}' not found in system PATH and not a valid direct path.")
            return None


def _run_command(command: List[str], cwd: Optional[str] = None, timeout_seconds: int = 3600) -> Tuple[bool, str, str]:
    """
    Executes a command using subprocess.
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
        if process.stderr: logger.debug(f"Command STDERR:\n{process.stderr.strip()}")

        if process.returncode == 0:
            logger.info(f"Command executed successfully: {cmd_str_for_log}")
            return True, process.stdout, process.stderr
        else:
            logger.error(f"Command failed with return code {process.returncode}: {cmd_str_for_log}")
            logger.error(f"STDERR output for failed command:\n{process.stderr.strip()}")
            return False, process.stdout, process.stderr
    except FileNotFoundError:
        logger.error(f"Command not found: {command[0]}. Ensure it's installed and in PATH or configured correctly.")
        return False, "", f"Command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout_seconds} seconds: {' '.join(command)}")
        return False, "", f"Command timed out after {timeout_seconds} seconds."
    except Exception as e:
        logger.error(f"An unexpected error occurred while running command {' '.join(command)}: {e}")
        return False, "", str(e)


def run_mafft(input_fasta_path: str, output_fasta_path: str, num_threads: int = 1, options: Optional[List[str]] = None) -> bool:
    mafft_path = _check_tool_path("mafft")
    if not mafft_path: return False
    if not os.path.exists(input_fasta_path):
        logger.error(f"MAFFT input file not found: {input_fasta_path}")
        return False

    command = [mafft_path, "--thread", str(num_threads), "--auto"]
    if options: command.extend(options)
    command.append(input_fasta_path)

    logger.info(f"Running MAFFT: input='{input_fasta_path}', output='{output_fasta_path}'")
    success, stdout_data, stderr_data = _run_command(command)

    if success and stdout_data:
        try:
            with open(output_fasta_path, "w") as f: f.write(stdout_data)
            logger.info(f"MAFFT alignment saved to {output_fasta_path}")
            if os.path.getsize(output_fasta_path) > 0: return True
            else:
                logger.error("MAFFT produced an empty output file.")
                if stderr_data: logger.error(f"MAFFT STDERR was:\n{stderr_data}")
                return False
        except IOError as e:
            logger.error(f"Failed to write MAFFT output to {output_fasta_path}: {e}")
            return False
    elif success and not stdout_data:
        logger.error("MAFFT ran successfully but produced no output.")
        if stderr_data: logger.error(f"MAFFT STDERR was:\n{stderr_data}")
        return False
    else: return False


def run_raxml_ng(alignment_phylip_path: str, model: str, prefix: str,
                 working_dir: Optional[str] = None, seed: int = 12345, threads: int = 1,
                 bootstrap_replicates: int = 0) -> Tuple[bool, Optional[str]]:
    raxml_ng_path = _check_tool_path("raxmlng")
    if not raxml_ng_path: return False, None
    if not os.path.exists(alignment_phylip_path):
        logger.error(f"RAxML-NG input MSA file not found: {alignment_phylip_path}")
        return False, None

    temp_dir_obj = None
    if not working_dir:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="raxml_")
        working_dir = temp_dir_obj.name
        logger.info(f"Using temporary directory for RAxML-NG: {working_dir}")
    elif not os.path.isdir(working_dir):
        try: os.makedirs(working_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Cannot create working directory for RAxML-NG: {working_dir} - {e}")
            return False, None

    msa_abs_path = os.path.abspath(alignment_phylip_path)
    output_prefix_for_cmd = os.path.join(working_dir, os.path.basename(prefix))

    command = [
        raxml_ng_path, "--msa", msa_abs_path, "--model", model,
        "--prefix", output_prefix_for_cmd, "--seed", str(seed),
        "--threads", "auto" if threads <=0 else str(threads), "--force",
    ]
    if bootstrap_replicates > 0:
        command.extend(["--bs-reps", str(bootstrap_replicates)])

    logger.info(f"Running RAxML-NG in {working_dir} with prefix {output_prefix_for_cmd}")
    success, stdout, stderr = _run_command(command, cwd=working_dir)

    best_tree_file = output_prefix_for_cmd + ".raxml.bestTree"
    final_tree_path = None

    if success and os.path.exists(best_tree_file):
        logger.info(f"RAxML-NG completed. Best tree: {best_tree_file}")
        final_tree_path = best_tree_file
        if temp_dir_obj:
            stable_output_dir = os.path.dirname(prefix) if os.path.dirname(prefix) else os.getcwd()
            os.makedirs(stable_output_dir, exist_ok=True)
            copied_tree_path = os.path.join(stable_output_dir, os.path.basename(prefix) + ".raxml.bestTree")
            try:
                shutil.copy2(best_tree_file, copied_tree_path)
                logger.info(f"Copied RAxML-NG best tree to {copied_tree_path}")
                final_tree_path = copied_tree_path
            except Exception as e_copy:
                logger.error(f"Error copying RAxML-NG results from temp dir: {e_copy}")
                final_tree_path = None # Indicate copy failure
    else:
        logger.error(f"RAxML-NG failed or best tree file not found at {best_tree_file}.")
        if stderr: logger.error(f"RAxML-NG STDERR:\n{stderr}")

    if temp_dir_obj: temp_dir_obj.cleanup()
    return bool(final_tree_path), final_tree_path


def parse_iqtree_model_finder_output(iqtree_report_file: str) -> Optional[str]:
    if not os.path.exists(iqtree_report_file):
        logger.error(f"IQ-TREE report file not found: {iqtree_report_file}")
        return None
    try:
        with open(iqtree_report_file, 'r') as f: content = f.read()
        bic_match = re.search(r"Best-fit model according to BIC:\s*([^\s]+)", content)
        if bic_match:
            model = bic_match.group(1).strip()
            logger.info(f"Found best model (BIC) in {iqtree_report_file}: {model}")
            return model
        aic_match = re.search(r"Best-fit model according to AIC:\s*([^\s]+)", content)
        if aic_match:
            model = aic_match.group(1).strip()
            logger.info(f"Found best model (AIC) in {iqtree_report_file}: {model}")
            return model
        logger.warning(f"Could not find best-fit model (BIC or AIC) in IQ-TREE report: {iqtree_report_file}")
        return None
    except Exception as e:
        logger.error(f"Error parsing IQ-TREE report file {iqtree_report_file}: {e}")
        return None

def parse_modeltest_ng_output(modeltest_ng_report_file: str) -> Optional[str]:
    if not os.path.exists(modeltest_ng_report_file):
        logger.error(f"ModelTest-NG report file not found: {modeltest_ng_report_file}")
        return None
    try:
        with open(modeltest_ng_report_file, 'r') as f: content = f.read()
        # Regex for format: "[BIC] Selected model: GTR+I+G4" or "Best model by BIC selection criterion : XYZ"
        # Prioritize BIC. ModelTest-NG output can be varied.
        # A common format: "Best model by BIC selection criterion : MODEL+PARAMS"
        # Or in a table summary. The line "MODEL_STRING <---- BEST (BIC)"
        bic_match = re.search(r"Best model by BIC selection criterion\s*:\s*([A-Za-z0-9+]+(?:\{\w+\/\w+\})?)", content)
        if bic_match:
            model = bic_match.group(1).strip()
            logger.info(f"Found best model (BIC) in {modeltest_ng_report_file}: {model}")
            return model
        # Simpler regex if the above is too specific, looking for a model string after BIC
        bic_generic_match = re.search(r"BIC\s*:\s*([A-Za-z0-9+]+)", content) # Might be too broad
        if bic_generic_match: # Be cautious with this one
             model = bic_generic_match.group(1).strip()
             logger.info(f"Found potential model (BIC, generic match) in {modeltest_ng_report_file}: {model}")
             return model
        logger.warning(f"Could not find clear best-fit model (BIC) in ModelTest-NG report: {modeltest_ng_report_file}.")
        return None
    except Exception as e:
        logger.error(f"Error parsing ModelTest-NG report file {modeltest_ng_report_file}: {e}")
        return None


def run_iqtree(alignment_path: str, prefix: str, working_dir: Optional[str] = None,
               sequence_type: Optional[str] = None, model: Optional[str] = "MFP",
               bootstrap_replicates: int = 0, threads: int = 1,
               run_model_finder_only: bool = False) -> Tuple[bool, Optional[str]]:
    iqtree_path = _check_tool_path("iqtree")
    if not iqtree_path: return False, None
    if not os.path.exists(alignment_path):
        logger.error(f"IQ-TREE input MSA file not found: {alignment_path}")
        return False, None

    temp_dir_obj = None
    if not working_dir:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="iqtree_")
        working_dir = temp_dir_obj.name
        logger.info(f"Using temporary directory for IQ-TREE: {working_dir}")
    elif not os.path.isdir(working_dir):
        try: os.makedirs(working_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Cannot create working directory for IQ-TREE: {working_dir} - {e}")
            return False, None

    msa_abs_path = os.path.abspath(alignment_path)
    output_prefix_for_cmd = os.path.basename(prefix)
    command = [iqtree_path, "-s", msa_abs_path, "--prefix", output_prefix_for_cmd,
               "-T", str(threads) if threads > 0 else "AUTO"]
    if sequence_type: command.extend(["-st", sequence_type])

    current_model_arg = model
    if run_model_finder_only and model != "MFP":
        logger.info("Forcing model to 'MFP' for run_model_finder_only=True.")
        current_model_arg = "MFP" # Ensure ModelFinder is run
    if current_model_arg: command.extend(["-m", current_model_arg])

    if bootstrap_replicates > 0 and not run_model_finder_only:
        command.extend(["-b", str(bootstrap_replicates)])

    logger.info(f"Running IQ-TREE in {working_dir} with command prefix {output_prefix_for_cmd}")
    success, stdout, stderr = _run_command(command, cwd=working_dir)

    effective_output_prefix = os.path.join(working_dir, output_prefix_for_cmd)
    iqtree_report_file = effective_output_prefix + ".iqtree"
    tree_file = effective_output_prefix + ".treefile"

    result_output = None # This will be model string or path to tree file

    if success:
        if run_model_finder_only or "MFP" in (current_model_arg or "").upper():
            if os.path.exists(iqtree_report_file):
                result_output = parse_iqtree_model_finder_output(iqtree_report_file)
                if not result_output: # Parsing failed, fallback to report file path
                    logger.warning(f"IQ-TREE model parsing failed, returning report file path: {iqtree_report_file}")
                    result_output = iqtree_report_file
            else:
                logger.error(f"IQ-TREE report file {iqtree_report_file} not found even after successful run.")
        elif os.path.exists(tree_file): # Not model finder, expect tree
            result_output = tree_file
            logger.info(f"IQ-TREE tree inference completed. Tree file: {tree_file}")
        elif os.path.exists(iqtree_report_file): # Fallback if tree not found but report is
             result_output = iqtree_report_file
             logger.warning(f"IQ-TREE treefile not found, but .iqtree report exists: {iqtree_report_file}")

        if result_output and temp_dir_obj and os.path.exists(result_output): # If it's a file path from temp dir
            stable_output_dir = os.path.dirname(prefix) if os.path.dirname(prefix) else os.getcwd()
            os.makedirs(stable_output_dir, exist_ok=True)
            copied_file_path = os.path.join(stable_output_dir, os.path.basename(result_output))
            try:
                shutil.copy2(result_output, copied_file_path)
                result_output = copied_file_path
            except Exception as e_copy:
                logger.error(f"Error copying IQ-TREE results from temp dir: {e_copy}")
                result_output = None # Failed to make output stable

    if temp_dir_obj: temp_dir_obj.cleanup()

    if not success or not result_output:
        logger.error(f"IQ-TREE execution failed or no primary output processed. Success: {success}, Result: {result_output}")
        if stderr and not success: logger.error(f"IQ-TREE STDERR:\n{stderr}") # Log stderr only if cmd failed
        return False, None

    return True, result_output


def run_modeltest_ng(alignment_phylip_path: str, output_base_name: str,
                     working_dir: Optional[str] = None, sequence_type: str = "DNA",
                     threads: int = 1) -> Tuple[bool, Optional[str]]:
    modeltest_ng_path = _check_tool_path("modeltest-ng")
    if not modeltest_ng_path: return False, None
    if not os.path.exists(alignment_phylip_path):
        logger.error(f"ModelTest-NG input MSA file not found: {alignment_phylip_path}")
        return False, None

    temp_dir_obj = None
    if not working_dir:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="modeltest_")
        working_dir = temp_dir_obj.name
        logger.info(f"Using temporary directory for ModelTest-NG: {working_dir}")
    elif not os.path.isdir(working_dir):
        try: os.makedirs(working_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Cannot create working directory for ModelTest-NG: {working_dir} - {e}")
            return False, None

    msa_abs_path = os.path.abspath(alignment_phylip_path)
    output_base_for_cmd = os.path.basename(output_base_name)
    command = [modeltest_ng_path, "-i", msa_abs_path, "-d", sequence_type.lower(),
               "-p", str(threads), "-o", os.path.join(working_dir, output_base_for_cmd)]

    logger.info(f"Running ModelTest-NG in {working_dir} with output base {output_base_for_cmd}")
    success, stdout, stderr = _run_command(command, cwd=working_dir)

    report_file_path = os.path.join(working_dir, output_base_for_cmd + ".out")
    result_output = None

    if success and os.path.exists(report_file_path):
        result_output = parse_modeltest_ng_output(report_file_path)
        if not result_output: # Parsing failed, fallback to report file path
            logger.warning(f"ModelTest-NG model parsing failed, returning report file path: {report_file_path}")
            result_output = report_file_path

        if temp_dir_obj and os.path.exists(result_output): # If it's a file path from temp dir
            stable_output_dir = os.path.dirname(output_base_name) if os.path.dirname(output_base_name) else os.getcwd()
            os.makedirs(stable_output_dir, exist_ok=True)
            copied_file_path = os.path.join(stable_output_dir, os.path.basename(result_output))
            try:
                shutil.copy2(result_output, copied_file_path)
                result_output = copied_file_path
            except Exception as e_copy:
                logger.error(f"Error copying ModelTest-NG results from temp dir: {e_copy}")
                result_output = None

    if temp_dir_obj: temp_dir_obj.cleanup()

    if not success or not result_output:
        logger.error(f"ModelTest-NG execution failed or no primary output processed. Success: {success}, Result: {result_output}")
        if stderr and not success: logger.error(f"ModelTest-NG STDERR:\n{stderr}")
        return False, None

    return True, result_output


if __name__ == '__main__':
    import re
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    dummy_fasta_content = """>seq1\nATGCATGCATGC\n>seq2\nATGGATGCATGC\n>seq3\nATGCATGCATGA\n"""
    dummy_phylip_content = """ 3 12\nseq1       ATGCATGCATGC\nseq2       ATGGATGCATGC\nseq3       ATGCATGCATGA\n"""

    with tempfile.TemporaryDirectory(prefix="treeweaver_tool_test_") as tmpdir:
        input_fasta = os.path.join(tmpdir, "input.fasta")
        input_phylip = os.path.join(tmpdir, "input.phy")
        with open(input_fasta, "w") as f: f.write(dummy_fasta_content)
        with open(input_phylip, "w") as f: f.write(dummy_phylip_content)
        logger.info(f"Test files created in {tmpdir}")
        mafft_success = False

        output_mafft_fasta = os.path.join(tmpdir, "aligned.fasta")
        logger.info("--- Testing MAFFT ---")
        if _check_tool_path("mafft"):
            mafft_success = run_mafft(input_fasta, output_mafft_fasta, num_threads=1)
            logger.info(f"MAFFT run success: {mafft_success}")
            if mafft_success: logger.debug(f"MAFFT Aligned output present at: {output_mafft_fasta}")
        else: logger.warning("MAFFT not configured, skipping test.")

        raxml_prefix = os.path.join(tmpdir, "raxml_test_run")
        logger.info("--- Testing RAxML-NG ---")
        if _check_tool_path("raxmlng"):
            raxml_input = input_phylip # Using unaligned for this basic test
            raxml_success, best_tree_file = run_raxml_ng(raxml_input, "GTR+G", raxml_prefix, threads=1)
            logger.info(f"RAxML-NG run success: {raxml_success}, Best tree: {best_tree_file}")
            if raxml_success and best_tree_file: logger.debug(f"RAxML-NG Best tree at: {best_tree_file}")
        else: logger.warning("RAxML-NG not configured, skipping test.")

        iqtree_prefix = os.path.join(tmpdir, "iqtree_mfp_run")
        logger.info("--- Testing IQ-TREE (ModelFinder) ---")
        if _check_tool_path("iqtree"):
            iq_input = input_phylip # Using unaligned for this basic test
            iq_success, iq_result = run_iqtree(iq_input, iqtree_prefix, model="MFP", threads=1, run_model_finder_only=True)
            logger.info(f"IQ-TREE ModelFinder run success: {iq_success}, Result: {iq_result}")
            if iq_success: logger.debug(f"IQ-TREE ModelFinder result: {iq_result}")
        else: logger.warning("IQ-TREE not configured, skipping test.")

        modeltest_output_base = os.path.join(tmpdir, "mt_run")
        logger.info("--- Testing ModelTest-NG ---")
        if _check_tool_path("modeltest-ng"):
            mt_input = input_phylip
            mt_success, mt_result = run_modeltest_ng(mt_input, modeltest_output_base, threads=1)
            logger.info(f"ModelTest-NG run success: {mt_success}, Result: {mt_result}")
            if mt_success: logger.debug(f"ModelTest-NG result: {mt_result}")
        else: logger.warning("ModelTest-NG not configured, skipping test.")

        logger.info(f"Test outputs are in {tmpdir}.")
pass
