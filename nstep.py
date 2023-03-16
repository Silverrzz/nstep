
import os
import time
import sys

try:
    import json
except:
    try:
        os.system("pip install json")
        import json
    except:
        print("Failed to install python modules, do you have python and pip installed?")
        exit()

try:
    import threading
except:
    try:
        os.system("pip install threading")
        import threading
    except:
        print("Failed to install python modules, do you have python and pip installed?")
        exit()

try:
    import subprocess
except:
    try:
        os.system("pip install subprocess")
        import subprocess
    except:
        print("Failed to install python modules, do you have python and pip installed?")
        exit()

try:
    import pickle
except:
    try:
        os.system("pip install pickle")
        import pickle
    except:
        print("Failed to install python modules, do you have python and pip installed?")
        exit()

try:
    import shutil
except:
    try:
        os.system("pip install shutil")
        import shutil
    except:
        print("Failed to install python modules, do you have python and pip installed?")
        exit()

try:
    from copy import deepcopy
except:
    try:
        os.system("pip install copy")
        from copy import deepcopy
    except:
        print("Failed to install python modules, do you have python and pip installed?")
        exit()   

try:
    from fabric import Connection
except:
    try:
        os.system("pip install fabric")
        from fabric import Connection
    except:
        print("Failed to install python modules, do you have python and pip installed?")
        exit()

class SSH_Client():
    def __init__(self, host, port, username, password):
        self.connection = Connection(
            host=host,
            user=username,
            port=port,
            connect_kwargs={
                "password": password
            }
        )

    def execute(self, command):
        result = self.connection.run(command)
        return result.stdout.strip()

    def upload(self, local_path, remote_path):
        self.connection.put(local_path, remote_path)

    def download(self, remote_path, local_path):
        self.connection.get(remote_path, local_path)

    def close(self):
        self.connection.close()

def connect_step_ssh(step):
    ssh_details = get_template()[step]["REMOTE"]
    if ssh_details["ssh_enabled"] == "false":
        return None
    ssh = SSH_Client(ssh_details["host"], ssh_details["port"], ssh_details["user"], ssh_details["pass"])
    return ssh

def get_execution_dir():
    for path in os.environ["PATH"].split(";"):
        if "nstep" in path:
            return path

def get_project_dir():
    exec_dir = get_execution_dir()
    cwd = os.getcwd()
    return cwd.replace(exec_dir, "")

def global_variable(name):
    #look through system PATH for nstep

    exec_dir = get_execution_dir()

    f = open(f"{exec_dir}/global-variables.json", "r")
    data = f.read()
    f.close()
    data = json.loads(data)
    return data[name]

class NSTEP_ProjectFile():
    def __init__(self):

        #open '.nstepignore' file and add all files and folders to a list
        self.ignore = []
        if os.path.exists("nstep/.nstepignore"):
            f = open("nstep/.nstepignore", "r")
            data = f.read()
            f.close()
            self.ignore = data.split("\n")


        self.project = {}

        #walk the current directory and add all files, folders and their content to a json structure
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith(".nstep"):
                    continue
                #check if the directory is a git directory
                file_path = os.path.join(root, file)
                file_path = file_path.replace("\\", "/")
                file_path = file_path[2:]
                
                if True in [True for ignore in self.ignore if ignore in file_path]:
                    log(f"Skipping {file} because it is in the ignore list", "DEBUG")
                    continue
                if file_path.startswith(".git"):
                    log(f"Skipping {file_path} because it is a git directory", "DEBUG")
                    continue
                log(f"Adding {file_path} to project file", "DEBUG")
                file_content = open(file_path, "rb").read()
                log(f"Saving content of {file_path} to project file", "DEBUG")
                self.project[file_path] = file_content

    def save(self):
        pickle.dump(self.project, open("project.nstep", "wb"))

    def load(self):
        self.project = pickle.load(open("project.nstep", "rb"))

    def construct(self):
        for file in self.project:
            line = ""
            split_text = file.split("/")
            split_text = split_text[:-1]
            for path in split_text:
                line += path + "/"
                create_dir(line)

            log(f"Writing content of {file}", "DEBUG")
            open(file, "wb").write(self.project[file])

class ProcessThread(threading.Thread):
    #killable threads
    def __init__(self, *args, **keywords):
        super(ProcessThread, self).__init__(*args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True

class logColours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GRAY = '\033[90m'

def log(message, t="INFO"):

    #if message ends with any line break, remove it
    if message.endswith("\r") or message.endswith("\n"):
        message = message[:-1]

    verbose = int(json.loads(open(get_execution_dir() + "/config.json", "r").read())["VERBOSE"])
    hour_minute_second = time.strftime("%H:%M:%S")
    if t == "OK":
        print(f"{logColours.GRAY}[{hour_minute_second}] {logColours.OKGREEN}[OK] {logColours.ENDC}{message}")
    elif t == "ERROR":
        print(f"{logColours.GRAY}[{hour_minute_second}] {logColours.FAIL}[ERROR] {message}{logColours.ENDC}")
    elif t == "INFO" and verbose > 0:
        print(f"{logColours.GRAY}[{hour_minute_second}] {logColours.OKBLUE}[INFO] {logColours.ENDC}{message}")
    elif t == "WARN" and verbose > 0:
        print(f"{logColours.GRAY}[{hour_minute_second}] {logColours.WARNING}[WARN] {message}{logColours.ENDC}")
    elif t == "DEBUG" and verbose > 1:
        print(f"{logColours.GRAY}[{hour_minute_second}] {logColours.GRAY}[DEBUG] {message}{logColours.ENDC}")
    elif verbose > 1:
        print(f"{logColours.GRAY}[{hour_minute_second}] {logColours.GRAY}[DEBUG] {message}")

def create_dir(dir_path, step=None):
    if step != None:
        ssh = connect_step_ssh(step)
        if ssh == None:
            if not os.path.exists(dir_path):
                os.mkdir(dir_path)
        else:
            response = ssh.execute(f"mkdir -p {dir_path}")
            log(f"Creating directory {dir_path} on {step}", "DEBUG")
    else:
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)

def remove_dir(dir_path, step=None):
    if step != None:
        ssh = connect_step_ssh(step)
        if ssh == None:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
        else:
            response = ssh.execute(f"rm -rf {dir_path}")
            log(f"Removing directory {dir_path} on {step}", "DEBUG")
    else:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)

def copy_file(file_path, dest_path, step=None):
    if step != None:
        ssh = connect_step_ssh(step)
        if ssh == None:
            shutil.copy(file_path, dest_path)
        else:
            response = ssh.upload(file_path, dest_path)
            log(f"Copying {file_path} to {dest_path} on {step}", "DEBUG")
    else:
        shutil.copy(file_path, dest_path)

def path_exists(path, step=None):
    if step != None:
        ssh = connect_step_ssh(step)
        if ssh == None:
            return os.path.exists(path)
        else:
            response = ssh.execute(f"ls {path}")
            if response == "":
                return False
            else:
                return True
    else:
        return os.path.exists(path)

class NSTEP_FileObject:
    def __init__(self, file, local_dir=None):
        if not os.path.exists(file):
            open(file, "w").close()

        self.root = file
        #remove path 
        self.name = os.path.basename(file).split(".")[0]
        self.ext = os.path.basename(file).split(".")[1]
        self.path = os.path.dirname(file)
        try:
            self.content = open(file, "r").read()
        except:
            self.content = ""
        self.feature = None

        if local_dir != None:
            self.local_dir = local_dir
        else:
            list_path = self.path.split("/")[1:]
            self.local_dir = "/".join(list_path)

    def save(self):
        open(self.root, "w").write(self.content)

def init():
    template = get_template()
    if template is None:
        #check if "project.nstep" exists
        if os.path.exists("project.nstep"):
            project = NSTEP_ProjectFile()
            project.load()
            project.construct()

        else:
            init_new_project()
    else:
        init_new_project(template)

def init_new_project(template=None):
    create_dir(".nstep/")
    create_dir(".nstep/scripts")

    f = open(".nstep/config.json", "w+")
    f.write(json.dumps(global_variable("DEFAULT_CONFIG"), indent=4))
    f.close()

    if template is None:
        default_template = global_variable("DEFAULT_TEMPLATE")
        default_steps = global_variable("DEFAULT_STEPS")
        open(".nstep/nstep-template.json", "w").write(json.dumps(default_template, indent=4))
        for step in default_steps:
            create_step(step)
        template = get_template()

        template[template["STEPS"][0]]["BUILD"] = "false"
        template[template["STEPS"][0]]["VOLATILE"] = "false"

        save_template(template)

    log("Initialized new project")
    log("Run 'nstep construct --all' to construct the project")
    

def get_template():
    if os.path.exists(".nstep/nstep-template.json"):
        return json.loads(open(".nstep/nstep-template.json").read())
    else:
        return None

def build(step: str = None):
    template = get_template()
    if step == "--all":
        build_all()
    elif step is None:
        log("Please specify a step to build", "ERROR")
    else:
        if build_step(step):
            time.sleep(0.1)
        else:
            log(f"Step {step} failed to build", "ERROR")

    
def build_all():
    log("Building all steps", "INFO")
    template = get_template()
    for step in get_steps(template):
        if build_step(step):
            time.sleep(0.1)
        else:
            log(f"Step {step} failed to build", "ERROR")
            return

    log("Finished building all steps", "OK")

def build_step(step):
    template = get_template()
    if step not in template["STEPS"]:
        log(f"Step {step} not found in template")
        sys.exit()

    if path_exists(get_step_directory(step), step):

        if template[step]["BUILD"] == "true":
            source_step = template["SOURCE_STEP"]
            if not path_exists(get_step_directory(source_step), source_step):
                log(f"{step.upper()} failed to build. It requires a complete build and assembly of {source_step.upper()}", "ERROR")
                return 0
            script_name = f"_build_{step}.nstep-script"
            parsed_script = parse_script(script_name, "RUN", [get_step_directory(source_step), get_step_directory(step), source_step, step])
            log(f"Building {step.upper()}", "INFO")
            execute_script(parsed_script, script_name)
        else:
            log(f"{step.upper()} is not marked as buildable", "WARN")

    else:
        log(f"{step.upper()} has not been assembled yet. Run 'nstep assemble {step}' to assemble it", "ERROR")

    return 1

def assemble_step(step):
    log(f"Assembling {step.upper()}", "INFO")
    template = get_template()
    #put together directory structure from template

    #delete old directory
    if template[step]["VOLATILE"] == "true" and template[step]["BUILD"] == "true":
        try:
            remove_dir(get_step_directory(step), step)
        except:
            pass

    time.sleep(0.3)

    create_dir(get_step_directory(step), step)
    
    assemble_segment(template[step]["STRUC"], step, get_step_directory(step) + "/")

def assemble_all():
    template = get_template()
    for step in get_steps(template):
        assemble_step(step)

def assemble_segment(segment, step, path):
    for item in segment:
        log(f"Creating {path + list(item.keys())[0]}", "DEBUG")
        segment_name = list(item.keys())[0]
        create_dir(path + segment_name, step)
        if "STRUC" in item[segment_name]:
            child = item[segment_name]["STRUC"]
            assemble_segment(child, step, path + segment_name + "/")
        else:
            log(f"End node {path + segment_name}", "DEBUG")

def get_step_directory(step):
    template = get_template()
    return template[step]["DIR"]

def get_steps(template):
    return template["STEPS"]

def get_step_from_path(path):
    template = get_template()
    steps = template["STEPS"]
    for step in steps:
        if path.startswith(template[step]["DIR"]):
            return step

def execute_script(script, script_name=None):
    log(f"Executing script {script_name}", "INFO")

    for command in script:
        log(f"Executing {command}", "DEBUG")
        process = command.split(" >> ")[0]

        if process == "CMD":
            #everything after the first >>, dont split any other >> in the command
            cmd_command = command.split(" >> ", 1)[1]
            log(f"Executing command {cmd_command}", "DEBUG")
            if int(json.loads(open(get_execution_dir() + "/config.json", "r").read())["VERBOSE"]) <= 1 and cmd_command.split(" ")[0] not in ["echo", "cd", "python"]:
                #runs with no console output
                result = subprocess.run(cmd_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if result.returncode != 0:
                    log(f"Command '{cmd_command}' failed to execute", "WARN")
                    log(result.stderr.decode("utf-8").replace("ERROR: ", ""), "WARN")
            else:
                #runs with console output
                os.system(cmd_command)

        elif process == "COPY":
            args = command.split(" >> ")[1:]

            def __func(i, o):
                dest_step = get_step_from_path(o)
                try:
                    copy_file(i, o, dest_step)
                    log(f"Copied {i} to {o}", "DEBUG")
                except Exception:
                    try:
                        create_dir(o, dest_step)
                        copy_file(i, o, dest_step)
                        log(f"Copied {i} to {o}", "DEBUG")
                    except Exception as e:
                        log(f"Failed to copy {i} to {o}", "ERROR")
                        log(e, "ERROR")
                        sys.exit()

            file_ref = args[0]

            if "*" in file_ref:
                input_files = get_input_attribute_data(args[0])

                for input_file in input_files:
                    i = input_file.feature
                    o = get_output_attribute_data(args[1], input_file)
                    __func(i, o)

            else:
                i = args[0]
                o = args[1]
                __func(i, o)
            
        elif process == "SCRIPT":
            args = command.split(" >> ")[1:]
            
            input_files = get_input_attribute_data(args[0])

            for input_file in input_files:
                i = input_file.feature
                o = get_output_attribute_data(args[1], input_file)
                if os.path.exists(".nstep/scripts/" + args[2] + ".nstep-script"):
                    script_name = args[2]
                    args_to_send = [i, o]
                    for arg in args[3:]:
                        args_to_send.append(arg)
                    log(f"Executing script {script_name} with arguments {args_to_send}", "INFO")
                    execute_script(parse_script(script_name+".nstep-script", "RUN", args_to_send), script_name + ".nstep-script")

            else:
                log(f"Script {args[2]} not found", "ERROR")
                sys.exit()
        else:
            log(f"Process {process} does not exist.", "ERROR")
            sys.exit()


def get_input_attribute_data(input_arg):
    #input_arg looks like this: "dir/dir/file:attribute" or "dir/*~attribute" or "dir/dir/*.py" or "dir/dir/asset.*" or "dir/dir/file"
    #there can be any combination of attributes and files
    #the file may also be a wildcard in which case all files matching the wildcard will be used and looped over
    #the attributes are the attributes of the file object
    #if the attribute is not part of the file object, load the previous attribute as json and find the attribute in there

    #get directory_string, file_string, attribute_string
    #directory_string is everything up to the last /
    if "/" in input_arg:
        directory_string = input_arg[:input_arg.rfind("/")]
        if ":" in input_arg:
            file_string = input_arg[input_arg.rfind("/")+1:input_arg.rfind(":")]
            attribute_string = input_arg[input_arg.rfind(":")+1:]
        else:
            file_string = input_arg[input_arg.rfind("/")+1:]
            attribute_string = ""
    else:
        file_string = "*"
        if ":" in input_arg:
            directory_string = input_arg[:input_arg.rfind(":")]
            attribute_string = input_arg[input_arg.rfind(":")+1:]
        else:
            directory_string = input_arg
            attribute_string = ""


    #get all files in directory_string
    files = walk_dir(directory_string.split("/")[0])
    #log(f"Files in {directory_string}: {files}", "DEBUG")
    files = [file for file in files if wildcard_stringmatch(file, directory_string + "/" + file_string)]

    #get all attributes in attribute_string

    data = []

    for file in files:
        file_object = get_file_object(file)
        if attribute_string == "":
            file_object.feature = file_object.root
            data.append(file_object)
        elif attribute_string == "_content":
            file_object.feature = file_object.content
            data.append(file_object)
        elif attribute_string == "_name":
            file_object.feature = file_object.name
            data.append(file_object)
        elif attribute_string == "_ext":
            file_object.feature = file_object.ext
            data.append(file_object)
        else:
            log(f"Attribute not found in file object: {attribute_string}", "WARN")

    return data


def get_output_attribute_data(output, input_file):
    
    output = output.replace("#", input_file.local_dir)
    output = output.replace("*:_name", input_file.name)
    output = output.replace("*:_ext", input_file.ext)
    output = output.replace("*:_content", input_file.content)

    if "*:" in output:
        #this is a custom attribute
        #isolate the attribute name then open up the file as json and get the attribute
        #the attribute name is after the : until a / . or the end of the string
        dummy = deepcopy(output)
        dummy = dummy.replace("/","@")
        dummy = dummy.replace(".","@")
        dummy = dummy[dummy.find("*:")+2:]
        attribute_name = dummy[:dummy.find("@")]

        json_data = json.loads(input_file.content)
        output = output.replace(f"*:{attribute_name}", json_data[attribute_name])


    output = output.replace("*", input_file.name + "." + input_file.ext)

    return output


    

def parse_script(script, func_name, args):
    script = ".nstep/scripts/" + script
    raw_script = open(script).read()
    raw_script = raw_script.replace("\n", "")
    raw_script = raw_script.replace("\t", "")
    #raw_script = raw_script.replace(" ", "")

    script_lines = raw_script.split(";")
    script_lines = [line for line in script_lines if line != ""]
    func_line = [line for line in script_lines if line.startswith(func_name)][0]
    definition_line = func_line[:func_line.find(":")]
    arg_map = definition_line[definition_line.find("{")+1:definition_line.find("}")]
    arg_map = arg_map.split(",")
    arg_map = [arg.split("-") for arg in arg_map]
    arg_map = {arg[0]:arg[1] for arg in arg_map}
    func_line = func_line[func_line.find(":")+1:]
    commands = func_line.split(",")
    parsed_commands = []
    for command in commands:
        for i, arg in enumerate(args):
            try:
                variable_name = f"${arg_map[str(i+1)]}"
                if variable_name in command:
                    command = command.replace(variable_name, arg)
            except:
                pass
        parsed_commands.append(command)

    log(f"Parsed commands: {parsed_commands}", "DEBUG")

    
    return parsed_commands

def wildcard_stringmatch(string_a, string_b):
    #log(f"Matching {string_a} to {string_b}", "DEBUG")
    if string_a.endswith("*") and string_a.count("*") == 1:
        if string_b.startswith(string_a[:string_a.find("*")]):
            return True
    elif string_a.startswith("*") and string_a.count("*") == 1:
        if string_b.endswith(string_a[string_a.find("*") + 1:]):
            return True
    elif string_b.endswith("*") and string_b.count("*") == 1:
        if string_a.startswith(string_b[:string_b.find("*")]):
            return True
    elif string_b.startswith("*") and string_b.count("*") == 1:
        if string_a.endswith(string_b[string_b.find("*") + 1:]):
            return True
    elif string_a == string_b:
        return True

    elif "*" in string_b:
        array_b = string_b.split("*")
        for section in array_b:
            a_find = string_a.find(section)
            if a_find == -1:
                return False
            else:
                string_a = string_a[a_find + len(section):]
        
        return True
    
    elif "*" in string_a:
        array_a = string_a.split("*")
        index = 0
        for section in array_a:
            b_find = string_b.find(section)
            if b_find == -1:
                return False
            elif b_find > index:
                index = b_find
            else:
                return False
        
        return True
    
    return False




def get_file_object(file_path):
    return NSTEP_FileObject(file_path)

def walk_dir(directory_string, files = []):
    #if directory_string is a file, return it
    if os.path.isfile(directory_string) and directory_string not in files:
        return [directory_string]
    for file in os.listdir(directory_string):
        
        if file not in files:
            if os.path.isdir(directory_string + "/" + file):
                files = walk_dir(directory_string + "/" + file, files)
            else:
                files.append(directory_string + "/" + file)

    #remove duplicates
    files = list(dict.fromkeys(files))

    return files

def walk_step_struc(struc, directory_string, files = []):
    for directory in struc:
        dir_name = [key for key in directory.keys()][0]
        if "STRUC" in directory[dir_name]:
            files = walk_step_struc(directory[dir_name]["STRUC"], directory_string + "/" + dir_name, files)
            [files.append(directory_string[2:] + "/" + dir_name + "/" + file) for file in os.listdir(directory_string + "/" + dir_name) if file not in files and os.path.isfile(directory_string + "/" + dir_name + "/" + file)]
        else:
            [files.append(directory_string[2:] + "/" + dir_name + "/" + file) for file in os.listdir(directory_string + "/" + dir_name) if file not in files and os.path.isfile(directory_string + "/" + dir_name + "/" + file)]

    return files






def watch_step(step):
    template = get_template()
    if template[step]["WATCH"] != "false":
        #watch the step
        log(f"Watching step {step.upper()}", "OK")
        watch_time = time.time()
        while True:
            #check if any files have been modified
            for file in walk_dir(step):
                if os.path.isfile(file):
                    if os.path.getmtime(file) > watch_time or os.path.getctime(file) > watch_time:
                        exe = template[step]["WATCH"]
                        log(f"Pausing watch for {step.upper()}", "INFO")
                        watch_time = time.time() + 10000
                        cmd = exe.split(" ")[0]
                        target = exe.split(" ")[1:]
                        target = " ".join(target)
                        if cmd == "release":
                            log(f"File {file} has been modified. Releasing {target}", "OK")
                            release_step(target)
                        elif cmd == "build":
                            log(f"File {file} has been modified. Building {target}", "OK")
                            build_step(target)
                        elif cmd == "run":
                            log(f"File {file} has been modified. Running {target}", "OK")
                            script_name = target.split(" ")[0] + ".nstep-script"
                            script_args = target.split(" ")[1:]
                            execute_script(parse_script(script_name, "RUN", script_args), script_name)
                        time.sleep(1)
                        log(f"Resuming watching {step.upper()}", "OK")
                        watch_time = time.time()

                        break

    else:
        log(f"Step {step} not watchable", "ERROR")
        sys.exit()

def save_template(template):
    with open(".nstep/nstep-template.json", "w") as f:
        f.write(json.dumps(template, indent=4))


def create_step(step):
    template = get_template()
    if step in template["STEPS"]:
        log(f"Step {step} already exists", "ERROR")
        sys.exit()
    else:
        template["STEPS"].append(step)
        step_config = global_variable("DEFAULT_STEP_CONFIG")
        step_config = json.dumps(step_config)
        step_config = step_config.replace("__STEP_NAME__", step)
        step_config = json.loads(step_config)
        template[step] = step_config
        save_template(template)

        with open(f".nstep/scripts/_build_{step}.nstep-script", "w+") as f:
            f.write(global_variable("DEFAULT_BUILD_SCRIPT"))

        if template["GIT"]["enabled"] == "true":
            #add new step to gitingore
            with open(".gitignore", "a") as f:
                f.write(f"{step}/\n")

            log(f"Added {step} to .gitignore", "INFO")

        log(f"Created {step.upper()}", "OK")

def remove_step(step):
    template = get_template()
    if step in template["STEPS"]:
        template["STEPS"].remove(step)
        del template[step]
        save_template(template)
        log(f"Removed {step.upper()}", "OK")
    else:
        log(f"{step.upper()} does not exist", "ERROR")
        sys.exit()

def modify_step(step, key, value):
    template = get_template()
    if step in template["STEPS"]:
        old_value = template[step][key]
        template[step][key] = value
        save_template(template)
        log(f"Modified {step.upper()} | {key.upper()}: {old_value} -> {value}", "OK")
    else:
        log(f"{step.upper()} does not exist", "ERROR")
        sys.exit()

def list_steps():
    template = get_template()
    for step in template["STEPS"]:
        log(f"{step.upper()}", "OK")
        

def info_step(step):
    template = get_template()
    if step in template["STEPS"]:
        log(f"Step: {step.upper()}", "OK")
        for key in template[step]:
            log(f"{key.upper()}: {template[step][key]}", "OK")
    else:
        log(f"{step.upper()} does not exist", "ERROR")
        sys.exit()

def duplicate_step(step, new_step):
    template = get_template()
    if step in template["STEPS"]:
        if new_step in template["STEPS"]:
            log(f"{new_step.upper()} already exists", "ERROR")
            sys.exit()
        else:
            #duplicate template
            template["STEPS"].append(new_step)
            template[new_step] = deepcopy(template[step])

            save_template(template)

            #duplicate scripts
            for script in os.listdir(".nstep/scripts"):
                if script.startswith("_") and f"_{step.upper()}." in script.upper():
                    shutil.copyfile(f".nstep/scripts/{script}", f".nstep/scripts/{script.replace(f'_{step.upper()}.', f'_{new_step.upper()}.')}")

            #add new step to gitingore
            if template["GIT"]["enabled"] == "true":
                with open(".gitignore", "a") as f:
                    f.write(f"{new_step}/\n")

                log(f"Added {new_step} to .gitignore", "INFO")

            log(f"Duplicated {step.upper()} to {new_step.upper()} successfully", "OK")
            log(f"Run 'nstep construct {new_step}' to construct {new_step.upper()}", "INFO")
    else:
        log(f"{step.upper()} does not exist", "ERROR")
        sys.exit()

def release_step(step):
    assemble_step(step)
    build_step(step)
    log(f"{step.upper()} released successfully", "OK")

def release_all():
    template = get_template()
    for step in template["STEPS"]:
        if template["SOURCE_STEP"] != step:
            release_step(step)

def construct_step(step):
    assemble_step(step)
    build_step(step)
    log(f"{step.upper()} constructed successfully", "OK")

def construct_all():
    template = get_template()
    for step in template["STEPS"]:
        construct_step(step)

def get_structure(json_struc, to_find):
    for d in json_struc:
        for key, value in d.items():
            if key == to_find:
                return value

    return False

# def add_structure(template, path):
#     # Split the path into a list of directories
#     dirs = path.split("/")
#     temp = deepcopy(template)

#     for d in dirs:
#         result = get_structure(template, d)
#         if result == False:
#             temp["STRUC"].append({d: {"STRUC": []}})
#             temp = get_structure(temp["STRUC"], d)
#         else:
#             temp = result
#     return template

def disect_structure(template, path, command, in_json=None):
    # Split the path into a list of directories

    if path == "":
        if command == "remove":
            template = []

        elif command == "replace":
            template = in_json

        elif command == "add":
            template.append(in_json)

        return template
    
    dirs = path.split("/")

    for d in dirs:
        i = 0
        for j in template:
            skip = False
            for key, value in j.items():
                if key == d:
                    if d == dirs[-1]:
                        if command == "remove":
                            template.pop(i)

                        elif command == "replace":
                            template[i][d]["STRUC"] = in_json

                        elif command == "add":
                            template[i][d]["STRUC"].append(in_json)

                        return template
                    else: 
                        template = template[i][d]["STRUC"]
                    skip = True
                    break

            if skip:
                break

        
                    
            i += 1

    log(f"Failed to process {path}", "ERROR")
    sys.exit()


def remove_structure(template, path):

    final = {}

    if path == "":
        return final

    dirs = path.split("/")[::-1]

    for i, d in enumerate(dirs):

        if d == dirs[0]:
            final = disect_structure(template, path, "remove")
        else:
            split_path = path.split("/")
            for j in range(i):
                split_path.pop()

            temp_path = ""
            for j in split_path:
                temp_path += j + "/"

            temp_path = temp_path[:-1] if temp_path[-1] == "/" else temp_path

            final = disect_structure(template, temp_path, "replace", final)

    return final

def add_structure(template, path):
    new_dir = path.split("/")[-1]
    path = path[:-len(new_dir)]
    if path != "":
        path = path[:-1] if path[-1] == "/" else path
        print ("path", path)
        dirs = path.split("/")[::-1]
    else:
        dirs = []

    final = disect_structure(template, path, "add", {new_dir: {"STRUC": []}})

    for i in range(len(dirs)-1):

        split_path = path.split("/")
        for j in range(i+1):
            split_path.pop()

        temp_path = ""
        for j in split_path:
            temp_path += j + "/"

        temp_path = temp_path[:-1] if temp_path[-1] == "/" else temp_path
        final = disect_structure(template, temp_path, "replace", final)

    return final

def git_init():
    template = get_template()
    if template["GIT"]["enabled"] == "false":
        log("Git is not enabled", "ERROR")
        log("Run 'nstep git config enabled true' to enable git", "ERROR")
        sys.exit()

    if os.path.exists(".git"):
        log("Git already initialized", "ERROR")
        sys.exit()

    log("Initializing a blank repository", "INFO")
    run_system_command("git init")
    log("Git initialized successfully", "OK")

    repository = template["GIT"]["repository"]
    branch = template["GIT"]["branch"]
    remote = template["GIT"]["remote"]

    if remote == "":
        remote = "origin"

    if repository == "":
        log("Created new blank repository", "OK")

    else:

        log("Adding remote", "INFO")
        run_system_command(f"git remote add {remote} {repository}")

        log("Pulling remote", "INFO")
        run_system_command(f"git pull -f {remote} {branch}")

        log(f"Checking out {remote}/{branch}", "INFO")
        run_system_command(f"git checkout {branch}")

        log(f"Set up remote {repository} successfully", "OK")

    f=open(".gitignore", "w+")
    f.write("BUILD/")
    f.close()


    log("Git configured successfully", "OK")

def run_system_command(command):

    if int(json.loads(open(get_execution_dir() + "/config.json", "r").read())["VERBOSE"]) <= 1 and command.split(" ")[0] not in ["echo", "cd", "python"]:
        #runs with no console output
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            log(f"Failed to run command {command}", "ERROR")
            log(result.stderr.decode("utf-8"), "ERROR")
            sys.exit()
    else:
        #runs with console output
        os.system(command)


    
if len(sys.argv) > 1:
    if sys.argv[1] == "init":
        init()

    elif sys.argv[1] == "assemble":
        if sys.argv[2] == "--all":
            assemble_all()
        else:
            assemble_step(sys.argv[2])

    elif sys.argv[1] == "build":
        if sys.argv[2] == "--all":
            build_all()
        else:
            build(sys.argv[2])

    elif sys.argv[1] == "watch":
        if len(sys.argv) >= 3:
            watch_step(sys.argv[2])
        else:
            log("No step specified", "ERROR")

    elif sys.argv[1] == "construct":
        if sys.argv[2] == "--all":
            construct_all()
        else:
            construct_step(sys.argv[2])       

    elif sys.argv[1] == "release":
        if sys.argv[2] == "--all":
            release_all()
        else:
            release_step(sys.argv[2])

    elif sys.argv[1] == "step":
        if sys.argv[2] == "-c":
            create_step(sys.argv[3])
        elif sys.argv[2] == "-r":
            remove_step(sys.argv[3])
        elif sys.argv[2] == "-m":
            new = sys.argv[5:]
            new = " ".join(new)
            modify_step(sys.argv[3], sys.argv[4], new)
        elif sys.argv[2] == "-l":
            list_steps()
        elif sys.argv[2] == "-i":
            info_step(sys.argv[3])
        elif sys.argv[2] == "-d":
            duplicate_step(sys.argv[3], sys.argv[4])

    elif sys.argv[1] == "mkdir":
        raw_path = sys.argv[2]
        step = raw_path.split("/")[0]
        directory = "/".join(raw_path.split("/")[1:])
        step_dir = get_step_directory(step)
        full_directory = step_dir + "/" + directory
        create_dir(full_directory, step)
        log(f"Created directory {directory} in {step.upper()}", "OK")
        #add to template
        template = get_template()
        template[step]["STRUC"] = add_structure(template[step]["STRUC"], directory)
        log(f"Added directory {directory} to template", "OK")
        save_template(template)

    elif sys.argv[1] == "rmdir":
        raw_path = sys.argv[2]
        step = raw_path.split("/")[0]
        directory = "/".join(raw_path.split("/")[1:])
        step_dir = get_step_directory(step)
        full_directory = step_dir + "/" + directory

        #remove from template
        template = get_template()
        template[step]["STRUC"] = remove_structure(template[step]["STRUC"], directory)
        log(f"Removed directory {directory} from template", "OK")
        save_template(template)
        remove_dir(full_directory, step)
        log(f"Removed directory {directory} in {step.upper()}", "OK")

    elif sys.argv[1] == "rndir":
        directory = sys.argv[2]
        new_directory = sys.argv[2].split("/")[0:-1] + [sys.argv[3]]
        new_directory = "/".join(new_directory)
        step = directory.split("/")[0]
        #remove from template
        template = get_template()
        template[step]["STRUC"] = remove_structure(template[step]["STRUC"], directory)
        
        #add renamed directory to template
        template[step]["STRUC"] = add_structure(template[step]["STRUC"], new_directory)

        log(f"Renamed directory {directory} to {new_directory} in template", "OK")
        save_template(template)

        shutil.move(directory, new_directory)
        log(f"Renamed directory {directory} to {new_directory} in {step.upper()}", "OK")

    elif sys.argv[1] == "config":
        if len(sys.argv) == 2:
            config_json = json.loads(open(get_execution_dir() + "/config.json", "r").read())
            print(json.dumps(config_json, indent=4))
        elif len(sys.argv) == 3:
            config_json = json.loads(open(get_execution_dir() + "/config.json", "r").read())
            print(json.dumps(config_json[sys.argv[2]], indent=4))
        elif len(sys.argv) == 4:
            setting = sys.argv[2].upper()
            config_json = json.loads(open(get_execution_dir() + "/config.json", "r").read())
            config_json[setting] = sys.argv[3]
            open(get_execution_dir() + "/config.json", "w").write(json.dumps(config_json, indent=4))
            log(f"Set {setting} to {sys.argv[3]}", "OK")

    elif sys.argv[1] == "git":

        if sys.argv[2] == "init":
            git_init()

        elif sys.argv[2] == "config":
            template = get_template()
            if len(sys.argv) == 3:
                print(json.dumps(template["GIT"], indent=4))
            elif len(sys.argv) == 4:
                print(json.dumps(template["GIT"][sys.argv[3]], indent=4))
            elif len(sys.argv) == 5:
                if template["GIT"]["enabled"] == "true":
                    if os.path.exists(".git"):
                        log("Editing the git configuration is not allowed while a repository is active", "ERROR")
                        log("To disable git, run 'nstep git remove'", "ERROR")
                        sys.exit()
                template["GIT"][sys.argv[3]] = sys.argv[4]
                save_template(template)
                log(f"Set git {sys.argv[3]} to {sys.argv[4]}", "OK")

        elif sys.argv[2] == "remove":
            result = subprocess.run(["powershell.exe", "Remove-Item", "-Recurse", "-Force", ".git"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                log("Failed to remove git repository", "ERROR")
                log("Error: " + result.stderr.decode("utf-8"), "ERROR")
                sys.exit()

            template = get_template()
            template["GIT"]["enabled"] = "false"
            save_template(template)
            log("Removed git repository", "INFO")
            log("Git is now disabled", "OK")

    elif sys.argv[1] == "export":
        log("Exporting project...", "INFO")
        project = NSTEP_ProjectFile()
        log("Saving project file...", "DEBUG")
        project.save()
        log("Project file saved at 'project.nstep'", "OK")

    elif sys.argv[1] == "script":
        if not sys.argv[2].endswith(".nstep-script"):
            script_name = sys.argv[2] + ".nstep-script"
        if os.path.exists(f".nstep/scripts/{script_name}"):
            execute_script(parse_script(script_name, "RUN", sys.argv[3:]), script_name)

        else:
            log(f"Script {script_name} does not exist", "ERROR")
            sys.exit()

    else:
        if not sys.argv[1].endswith(".nstep-script"):
            script_name = sys.argv[1] + ".nstep-script"
        if os.path.exists(f".nstep/scripts/{script_name}"):
            log(f"Running script {script_name}", "OK")
            execute_script(parse_script(script_name, "RUN", sys.argv[2:]), script_name)

        else:
            args_string = ""
            for arg in sys.argv[1:]:
                args_string += arg + " "

            log(f"{sys.argv[1]} is neither a valid command nor a script", "ERROR")
            log(f"Command: {args_string}", "ERROR")
            sys.exit()
else:
    log("No command specified", "INFO")
    log("If you're using this to verify a correct installation, congrats - all is working as expected :)", "OK")
