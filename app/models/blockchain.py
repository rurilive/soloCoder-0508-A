import hashlib
import json
from time import time
from typing import Any, Dict, List, Optional
from datetime import datetime

from flask import current_app
import sqlite3


def get_db():
    conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    return conn


class Block:
    def __init__(self, index: int, timestamp: float, data: Dict[str, Any], previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine_block(self, difficulty: int = 4) -> None:
        target = '0' * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }


class Blockchain:
    def __init__(self, difficulty: int = 2):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self._load_chain()
        if not self.chain:
            self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        genesis_block = Block(0, time(), {'type': 'genesis'}, '0')
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        self._save_block(genesis_block)

    def _load_chain(self) -> None:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM blockchain ORDER BY "index" ASC
        ''')
        blocks = cursor.fetchall()
        conn.close()
        
        for block in blocks:
            loaded_block = Block(
                index=block['index'],
                timestamp=block['timestamp'],
                data=json.loads(block['data']),
                previous_hash=block['previous_hash'],
                nonce=block['nonce']
            )
            loaded_block.hash = block['hash']
            self.chain.append(loaded_block)

    def _save_block(self, block: Block) -> None:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO blockchain (index, timestamp, data, previous_hash, nonce, hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            block.index,
            block.timestamp,
            json.dumps(block.data),
            block.previous_hash,
            block.nonce,
            block.hash
        ))
        conn.commit()
        conn.close()

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, data: Dict[str, Any]) -> Block:
        new_block = Block(
            index=len(self.chain),
            timestamp=time(),
            data=data,
            previous_hash=self.get_latest_block().hash
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self._save_block(new_block)
        return new_block

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            if current_block.hash != current_block.calculate_hash():
                return False
            
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True

    def get_blocks_by_event_id(self, event_id: int) -> List[Block]:
        return [block for block in self.chain if block.data.get('event_id') == event_id]


def init_blockchain_table() -> None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blockchain (
            "index" INTEGER PRIMARY KEY,
            timestamp REAL NOT NULL,
            data TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            nonce INTEGER NOT NULL,
            hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def add_event_note_to_blockchain(event_id: int, note: str, created_by: str = 'system') -> Dict[str, Any]:
    blockchain = Blockchain()
    data = {
        'type': 'event_note',
        'event_id': event_id,
        'note': note,
        'created_by': created_by,
        'created_at': datetime.now().isoformat()
    }
    block = blockchain.add_block(data)
    return block.to_dict()


def get_event_notes_from_blockchain(event_id: int) -> List[Dict[str, Any]]:
    blockchain = Blockchain()
    blocks = blockchain.get_blocks_by_event_id(event_id)
    notes = []
    for block in blocks:
        if block.data.get('type') == 'event_note':
            notes.append({
                'note': block.data.get('note'),
                'created_by': block.data.get('created_by'),
                'created_at': block.data.get('created_at'),
                'block_hash': block.hash,
                'block_index': block.index
            })
    return sorted(notes, key=lambda x: x['created_at'], reverse=True)


def get_blockchain_status() -> Dict[str, Any]:
    blockchain = Blockchain()
    return {
        'length': len(blockchain.chain),
        'is_valid': blockchain.is_chain_valid(),
        'latest_block': blockchain.get_latest_block().to_dict()
    }
