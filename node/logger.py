import logging

logger = logging.getLogger(__name__)

def configure_logger(node_id):
    logging.basicConfig(
        level=logging.INFO,
        format=f'node-{node_id} - %(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'node-{node_id}/log.log', mode='a')
        ]
    )
