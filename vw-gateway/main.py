#!/usr/bin/python3
from thingsboard_gateway.gateway.tb_gateway_service import TBGatewayService
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader
import argparse
import os.path
from pyfiglet import Figlet

# "/home/sanaz/viraweb123/odoo-iot/vw-gateway/extensions"

def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist! Use the --help flag for input options." % arg)
    else:
        return arg  # return an open file handle
    

parser = argparse.ArgumentParser()
parser.add_argument("--config",
                    help='Path To config.yaml',
                    default = './conf.yaml',
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
                    help='The program version is 1.0.0',
                    ) 

args = parser.parse_args()  

f = Figlet(font='big')
print (f.renderText('ViraWeb123')) 


TBModuleLoader.PATHS.append(args.extension)

TBGatewayService(args.config)


#TBModuleLoader.PATHS.append("/home/sanaz/viraweb123/odoo-iot/vw-gateway/extensions")

#TBGatewayService("/home/sanaz/viraweb123/odoo-iot/vw-gateway/ubuntu/configs/conf.yaml")


#  viraweb123/odoo-iot/vw-gateway                  $ python main.py --config ../configs/conf.yaml    

# python ../viraweb123/odoo-iot/vw-gateway/main.py --config ../tools/configs/conf.yaml --extension ../Videos/extensions

#TBGatewayService('../configs/conf.yaml')
