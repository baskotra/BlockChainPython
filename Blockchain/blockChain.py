from time import time
import json
import hashlib
from flask import Flask, jsonify, request
from uuid import uuid4
from textwrap import dedent
from urllib.parse import urlparse

class Blockchain():
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        #* Add the first block without any predecessors
        self.new_block(previous_hash=1,proof=100)
    
    def register_node(self, address):
        """
        Register a new node with some URL.
        :param address: <str> eg: http://192.168.1.1:500
        :return: None
        """
        parsed_url = parsed_url(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self,chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print('f{las_block}')
            print('f{block}')
            print('')
            #* Check if the hash of the block is correct?
            if block['previous_hash'] != self.hash(last_block):
                return False
            
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            
            last_block = block
            current_index +=1
        
        return True
    
    def resolve_conflict(self):
        neighbours = self.nodes
        new_chain = None

        #* Looking for chains longer than ours
        max_length = len(self.chain)

        #* Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = request.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        
        #* Replace our chain with the longest and valid chain
        if new_chain:
            self.chain = new_chain
            return True
    
        return False


    def new_block(self,previous_hash, proof):
        """ 
        Adds a new block with the index of th current block
        timstamp at which it was sent,
        adds the transaction, proof and the hash of previous block
        """

        block = {
            'index':len(self.chain)+1,
            'timestamp':time(),
            'transaction':self.current_transactions,
            'proof':proof,
            'previous_hash':previous_hash or self.hash(self.chain[-1])
        }

        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self,sender,recipient,amount):
        self.current_transactions.append({
            'sender':sender,
            'receiver':recipient,
            'amount':amount,
        })
        return self.last_block['index']-1 

    def proof_of_work(self, last_proof):
        """
        :params last_proof: <int>
        :returns : <int>
        """
        proof = 0
        while self.valid_proof(last_proof,proof) is False:
            proof +=1
        
        return proof
    
    @staticmethod
    def valid_proof(last_proof,proof):
        """
        Checks if the last_proof, and proof gives the leading 4 Zeros
        :params last_proof, proof: <int>
        :returns : <bool>
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of block
        :param block: <dict> block
        :return: <str>
        """
        
        #* We need to make sure the dictionary is consistent, else hashes would be incorrect
        block_string = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

#* Instantiate our Node
app = Flask(__name__)

#* Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-',"")

#* Instantiate Blockchain
blockchain = Blockchain()

@app.route('/mine',methods=['GET'])
def mine():
    #* We must run a proof of work to get next proof of work
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    #* We must receive a reward for finding the proof.
    #* The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )
    
    #* Forge the new block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(previous_hash,proof)
    response = {
        'message':'New block is minted',
        'index': block['index'],
        'transaction': block['transaction'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/transaction/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender','recipient','amount']

    #* To check if the requried files are in the POST'd data
    if not all(k in values for k in required):
        return 'Missing Values', 400
    
    #* Create a new Transaction
    index = blockchain.new_transaction(values['sender'],values['recipient'],values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return response, 201

@app.route('/chain',methods=['GET'])
def chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response),200

@app.route('/nodes/register', methods=['POST'])
def register_node():
    value = request.get_json()
    nodes = value.get('nodes')

    if nodes is None:
        return "ERROR: Return a valid list of nodes", 400
    
    for node in nodes:
        blockchain.register_node(node)
    
    response = {
        'message': "New nodes have been registered successfully",
        'nodes': list(blockchain.nodes),
    }
    
    return jsonify(response), 201

@app.route('/nodes/resolve',methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflict

    if replaced:
        response = {
            'message': "Our chain was replaced.",
            'chain': blockchain.chain,
        }
    else:
        response = {
            'message': "Our chain is authoritative",
            'chain': blockchain.chain,
        }
    return response, 200

if __name__ == '__main__':
    app.run(host='localhost',port=5000)
