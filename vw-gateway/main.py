#!/usr/bin/python3
from thingsboard_gateway.gateway.tb_gateway_service import TBGatewayService
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader
import argparse
import os.path
from pyfiglet import Figlet
import pkg_resources


# "/home/sanaz/viraweb123/odoo-iot/vw-gateway/extensions"

def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist! Use the --help flag for input options." % arg)
    return arg
    

parser = argparse.ArgumentParser()
parser.add_argument("--config",
                    help='Path To config.yaml',
                    default = False,
                    required=True,
                    type=lambda x: is_valid_file(parser, x)
                    ) 

parser.add_argument("--extension",
                    help='Path To extensions folder',
                    default = '.',
                    required=True,
                    type=lambda x: is_valid_file(parser, x)
                    ) 

parser.add_argument("--version",
                    help='The program version is {}'.format(pkg_resources.get_distribution("thingsboard-gateway").version),
                    ) 

args = parser.parse_args()  

print("""
{logo}
---------------------------
Thingsboard Gateway
version     : {version}
extensions  : {extensions_path}
config      : {config_path} 
""".format(
    logo=Figlet(font='big').renderText('ViraWeb123'), 
    version=pkg_resources.get_distribution("thingsboard-gateway").version,
    extensions_path= args.extension,
    config_path= args.config
))


TBModuleLoader.PATHS.append(args.extension)
TBGatewayService(args.config)