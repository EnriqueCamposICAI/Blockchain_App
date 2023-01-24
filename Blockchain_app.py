import Blockchain as BC

import socket
from flask import Flask, jsonify, request
from argparse import ArgumentParser
from threading import Semaphore, Thread
import json
import time
import requests
import platform


mutex_blockchain = Semaphore(1)

# Instancia del nodo
app = Flask(__name__)

# Instanciacion de la aplicacion
blockchain = BC.Blockchain()

# Para saber mi ip
mi_ip = socket.gethostbyname(socket.gethostname())

nodos_red = set()


def copia_seguridad():
    '''
    Esta función realiza una copia de seguridad de la blockchain cada 60s
    Se ha tenido que crear un hilo paralelo a la ejecución del servidor
    '''

    while app_run:

        # Se bloquea el acceso a la blockchain (no se podrá editar)
        mutex_blockchain.acquire()
        copia = {
            'chain': [b.toDict()
                      for b in blockchain.bloques if b.hash is not None],
            'longitud': len(blockchain.bloques),
            'date': time.strftime('%d/%m/%Y %H:%M:%S')
        }
        # Se guarda la blockchain en un diccionario y luego en un json
        name = (nodo_actual.split('//')[1]).split(':')
        with open(f'respaldo-nodo-{name[0]}-{name[1]}.json', 'w') as file:
            json.dump(copia, file, indent=4)

        mutex_blockchain.release()
        # Se libera la blockchain

        # Cada segundo se comprobará si se ha acabado la ejecución de la app
        # Hasta llegar a 60s, que realiza una nueva copia de seguridad
        i = 60
        while i > 0 and app_run:
            time.sleep(1)
            i -= 1


def resuelve_conflictos():
    '''
    Esta función resuelve los conflictos de la blockchain, comprobando si hay
    alguna blockchain más larga que la de nuestro nodo en la red.
    Dicha comprobación se llevará a cabo cada vez que se mine un bloque

    :return bool: Especifica si las cadenas están correctamente sincronizadas
    '''
    global blockchain
    global nodos_red

    # No se necesita semáforo ya que ya lo tiene minar

    # Hay que mirar la blockchain de los demás nodos
    # Primero el tuyo (se da por hecho que es la más larga)

    longitud_actual = len(blockchain.bloques)
    posible_blockchain = None

    # Se comparan todas las blockchains de los nodos
    # Si la longitud es mayor, se cambia la blockchain actual

    for nodo in nodos_red:
        response_nodo = requests.get(f'{nodo}/chain')

        if response_nodo.status_code == 200:

            if response_nodo.json()['longitud'] > longitud_actual:
                posible_blockchain = response_nodo.json()['chain']
                longitud_actual = response_nodo.json()['longitud']

    if posible_blockchain is not None:
        # Hay que cambiar la blockchain por la nueva
        # Como en actualizar nodo se pedía que se hiciera bloque a bloque,
        # aquí también. Como el primer bloque es el mismo
        # para todos, se pasa directamente al segundo

        blockchain_nueva = BC.Blockchain()
        cadena = posible_blockchain[1:]

        # Se usan los datos de la blockchain nueva

        for bloque in cadena:

            bloque_nuevo = BC.Bloque(
                bloque['indice'], bloque['transacciones'],
                bloque['timestamp'], bloque['hash_previo'])
            nuevo_hash = blockchain_nueva.prueba_trabajo(bloque_nuevo)

            # Se comprueba el hash en caso de no coincidir se rompe
            # (no se llega a cambiar la blockchain)
            if nuevo_hash != bloque['hash']:
                return 'Error: La cadena de bloques no es valida', 400

            else:
                blockchain_nueva.integra_bloque(bloque_nuevo, nuevo_hash)

        blockchain.bloques = blockchain_nueva.bloques
        return True
    else:
        return False


@app.route('/transacciones/nueva', methods=['POST'])
def nueva_transaccion():
    '''
    Esta función registra transaccioens nuevas en la blcokchain
    '''
    values = request.get_json()

    # Comprobamos que todos los datos de la transaccion estan
    required = ['origen', 'destino', 'cantidad']

    if not all(k in values for k in required):
        return 'Faltan valores', 400

    # Creamos una nueva transaccion aqui

    index = blockchain.nueva_transaccion(
        values['origen'], values['destino'], values['cantidad'])

    response = {
        'mensaje': f'La transacción se incluirá en el bloque de indice {index}'
               }

    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def blockchain_completa():
    '''
    Esta función devuelve la cadena de blockchain completa hasta ahora.
    '''
    response = {
        # Solamente permitimos la cadena de aquellos
        # bloques finales que tienen hash
        'chain': [b.toDict()
                  for b in blockchain.bloques if b.hash is not None],
        'longitud': len(blockchain.bloques),
        # longitud de la cadena
                }
    return jsonify(response), 200


@app.route('/minar', methods=['GET'])
def minar():
    '''
    Esta función mina un bloque nuevo en la blockchain, usando las
    transacciones pendientes y la recompensa al nodo que mina.
    '''
    # No hay transacciones

    if len(blockchain.trans_por_hacer) == 0:
        response = {
            'mensaje':
            "No es posible crear un nuevo bloque. No hay transacciones"
                    }

    else:
        # Hay transacción por lo que, ademas de minar el bloque,
        # recibimos recompensa

        mutex_blockchain.acquire()

        # Las transacciones no se borran. Minar para integrar el nuevo bloque
        previous_hash = blockchain.bloques[-1].hash

        # Recibimos un pago por minar el bloque.
        # Creamos una nueva transaccion con:
        # Dejamos como origen el 0
        # Destino nuestra ip # Cantidad = 1

        # [Completar el siguiente codigo]

        transacciones = blockchain.trans_por_hacer

        pago = {'origen': 0, 'destino': mi_ip, 'cantidad': 1}

        blockchain.nueva_transaccion(
            pago['origen'], pago['destino'], pago['cantidad'])

        # Creamos el nuevo bloque
        bloque = blockchain.nuevo_bloque(previous_hash)
        hash_bloque = blockchain.prueba_trabajo(bloque)

        # Se comprueba que no haya conflictos con el resto de nodos de la red
        if resuelve_conflictos():
            response = {
                'mensaje': "Ha habido un conflicto. Esta cadena se ha" +
                " actualizado con una version mas larga. Volver a minar " +
                "para guardar las transacciones"
            }
            blockchain.trans_por_hacer = transacciones
            # Se usan las mismas transacciones que antes de minarr
            # (se ha borrado la recompensa, no se mina)
        else:

            # Como no hay fallos, se integra el bloque
            correcto = blockchain.integra_bloque(bloque, hash_bloque)
            blockchain.trans_por_hacer = []

            if correcto:
                response = {
                    'mensaje': "Nuevo Bloque Minado",
                    'indice': bloque.indice,
                    'transacciones': bloque.transacciones,
                    'hash': hash_bloque,
                    'prueba': bloque.prueba,
                    'hash_previo': bloque.hash_previo,
                    'timestamp': bloque.timestamp
                }
            else:
                response = {
                    'mensaje': "Error al minar el bloque"
                }

        mutex_blockchain.release()
        # Se desbloquea la blockchain
    return jsonify(response), 200


@app.route('/nodos/registrar', methods=['POST'])
def registrar_nodos_completo():
    '''
    Mediante el método POST, almacena los nodos de values (lista de URLS)
    dentro de nodos_red, enviándoles la blockchain correspondiente
    '''
    values = request.get_json()
    global blockchain
    global nodos_red

    nodos_nuevos = values.get('direccion_nodos')
    if nodos_nuevos is None:
        return "Error: No se ha proporcionado una lista de nodos", 400

    # Se añaden los nuevos nodos a la red

    for nodo in nodos_nuevos:
        nodos_red.add(nodo)

    # Se añade el nodo actual (para mandar a los
    # nuevos nodos la blockchain actual)

    nodos_red.add(nodo_actual)

    try:
        for nodo in nodos_nuevos:
            nodos_red.discard(nodo)  # No hay que enviar el nodo a si mismo

            data = {'nodos_direcciones': list(
                nodos_red), 'blockchain':
                [b.toDict() for b in blockchain.bloques if b.hash is not None]}
            # Se manda la blockchain actual a los nuevos nodos
            response = requests.post(nodo+"/nodos/registro_simple",
                                     data=json.dumps(data),
                                     headers={'Content-type':
                                              'application/json'})

            nodos_red.add(nodo)
            # Se vuelve a mandar el nodo actual a la lista de nodos
        nodos_red.discard(nodo_actual)
        all_correct = True
    except:
        all_correct = False

    if all_correct:
        response = {'mensaje': 'Se han incluido nuevos nodos en la red',
                    'nodos_totales': list(nodos_red)}
    else:
        response = {'mensaje': 'Error notificando el nodo estipulado', }

    return jsonify(response), 201


@app.route('/nodos/registro_simple', methods=['POST'])
def registrar_nodo_actualiza_blockchain():
    '''Similar a la función anterior, pero tiene un objetivo complementario,
    ya que incluye el propio nodo dentro del diccionario JSON que representa
    la cadena hasta el momento
    '''
    # Obtenemos la variable global de blockchain
    global blockchain
    global nodos_red

    read_json = request.get_json()
    nodes_addreses = read_json.get("nodos_direcciones")

    # [...] Codigo a desarrollar

    # Se añade cada nodo a la red

    for node in nodes_addreses:
        nodos_red.add(node)

    # Se actualiza la blockchain por la nueva

    blockchain_leida = read_json.get("blockchain")
    blockchain_nueva = BC.Blockchain()

    # Como el primer bloque es el mismo para todos, se añade
    # directamente y se pasa al siguiente
    cadena = blockchain_leida[1:]

    for bloque in cadena:

        bloque_nuevo = BC.Bloque(
            bloque['indice'], bloque['transacciones'],
            bloque['timestamp'], bloque['hash_previo'])
        nuevo_hash = blockchain_nueva.prueba_trabajo(bloque_nuevo)

        if nuevo_hash != bloque['hash']:
            return 'Error: La cadena de bloques no es valida', 400

        else:
            blockchain_nueva.integra_bloque(bloque_nuevo, nuevo_hash)

    # [...] fin del codigo a desarrollar -> blockchain leida

    if blockchain_nueva is None:

        return "El blockchain de la red esta currupto", 400
    else:
        # Aquí se va a editar la blockchain así que se bloquea el acceso
        mutex_blockchain.acquire()
        blockchain.bloques = blockchain_nueva.bloques.copy()
        mutex_blockchain.release()
        string = "La blockchain del nodo"
        string += str(mi_ip)
        string += ":"
        string += str(puerto)
        string += "ha sido correctamente actualizada"
        return string, 200


@app.route('/system', methods=['GET'])
def system():
    '''Usando la librería platform, obtiene los datos del sistema
    y los devuelve en formato JSON

    :return Objeto JSON con los datos del sistema
    '''
    info_sistema = platform.uname()
    response = {
        "maquina": info_sistema.machine,
        "nombre_Sistema": info_sistema.system,
        "version": info_sistema.version,
    }
    return jsonify(response), 200


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument('-p', '--puerto', default=5000,
                        type=int, help='puerto para escuchar')

    args = parser.parse_args()
    puerto = args.puerto

    # Por defecto (flask) -> se ha metido a mano
    nodo_actual = f"http://{mi_ip}:{puerto}"

    # Crear el hilo de la copia de seguridad

    app_run = True
    hilo_copia = Thread(target=copia_seguridad)
    hilo_copia.start()
    app.run(host='0.0.0.0', port=puerto)
    app_run = False
    hilo_copia.join()
    exit(0)
