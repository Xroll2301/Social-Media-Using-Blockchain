import hashlib
import time
import json

def hash_block(index, posts, previous_hash):
    """Hashes a block by converting its data into a string."""
    block_string = f"{index}{json.dumps(posts)}{previous_hash}".encode('utf-8')
    return hashlib.sha256(block_string).hexdigest()

class Blockchain:
    def __init__(self):
        """Initializes the blockchain with the genesis block."""
        self.chain = []
        self.posts = []  # Holds pending posts (either IPFS CID or text)
        self.create_block(previous_hash='0')  # Genesis block

    def create_block(self, previous_hash):
        """Creates a new block, adds posts to it, and appends it to the chain."""
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),

            'posts': self.posts,
            'previous_hash': previous_hash,
            'hash': hash_block(len(self.chain) + 1, self.posts, previous_hash)
        }
        self.posts = []  # Reset the posts after adding to the block
        self.chain.append(block)

        # Save the new block to logs.txt
        self.save_block_to_log(block)

        # Save the full blockchain to logs.txt
        self.save_chain_to_log()

        return block

    def add_post(self, content):
        """Adds a post (either IPFS CID or text) to the pending posts list."""
        self.posts.append(content)
        return len(self.chain) + 1

    def get_previous_block(self):
        """Returns the most recent block in the chain."""
        return self.chain[-1] if self.chain else None

    def save_block_to_log(self, block):
        """Saves the latest block to logs.txt."""
        with open("logs.txt", "a") as log_file:
            log_file.write(f"New Block Mined:\n{json.dumps(block, indent=4)}\n\n")

    def save_chain_to_log(self):
        """Saves the entire blockchain to logs.txt."""
        with open("logs.txt", "w") as log_file:
            log_file.write("Full Blockchain:\n")
            log_file.write(json.dumps(self.chain, indent=4))
