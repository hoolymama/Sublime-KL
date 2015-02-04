import re, time, sys
import textwrap
from telnetlib import Telnet
import sublime, sublime_plugin

class maya_update_klCommand(sublime_plugin.TextCommand):
    '''
    ST3 Plugin to update current file's KL code in Maya

    This is achieved by preparing and sending python
    code that calls setKLOperatorFile on all SpliceMaya 
    nodes that have an entry operator that exists in this 
    file.

    A nice way to use this plugin is with a hook that
    is triggered on file save. You can install the 
    sublime-hooks plugin using PackageInstaller.
    https://github.com/twolfson/sublime-hooks. Then add
    the following to KL.sublime-settings 
    {
    "on_post_save_language": [
    {
        "command": "maya_update_kl"
    }
    ]
    }

    The command port 7002 must be a python port open in maya.
    For example, do this in the script editor first:
    from maya import cmds
    cmds.commandPort(name=":7002", sourceType="python")

    Note: In the python code in the TEMPLATE, the only way I 
    found to get the entry operator for a maya node is by 
    interrogating the "saveData" attribute. Unfortunately, 
    this is only available after the scene has been saved.
    '''


    TEMPLATE = textwrap.dedent('''
        import pymel.core as pm
        import json
        nodes = pm.ls(type="spliceMayaNode")
        for node in nodes:
            datadict = json.loads(node.saveData.get())
            entry_operator =  datadict['nodes'][0]['bindings'][0]['operator']['entry']
            if entry_operator in {1}:
                jsonstr = '{{"opName": "'+entry_operator+'", "fileName": "{0}"}}'
                pm.fabricSplice('setKLOperatorFile', node, jsonstr)
    ''')

    def run(self, edit):
        '''
        Generate and send code to update Splice nodes in Maya

        First get the fileName and an array of operator names.
        These are injected into the above template, which is 
        sent to a port on the localhost using Telnet.
        '''
        file_path = self.view.file_name()
        regions = self.view.find_all('^operator\s+.*$', 0)
        operators = []
        for region in regions:
            region_str = self.view.substr(region)
            m = re.search('^operator\s+([a-zA-Z0-9_]+).*$', region_str)
            if m:
                operators.append(m.groups()[0])
        
        op_str = '['+ ','.join('"'+op+'"' for op in operators) + ']'

        cmd = self.TEMPLATE.format(
            file_path, op_str).encode(encoding='UTF-8')

        conn = None
        host = '127.0.0.1'
        port = 7002
        try:
            conn = Telnet(host, port, timeout=3)
            conn.write(cmd)
        except Exception:
            ex = sys.exc_info()[1]
            error = str(ex)
            sublime.error_message(
                "Can't communicate with Maya %d. %s" % (port, error))
            raise
        else:
            time.sleep(.1)
        finally:
            if conn is not None:
                conn.close()
