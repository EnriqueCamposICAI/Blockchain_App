import json
import hashlib
import time


class Bloque:
    def __init__(self, indice: int, transacciones: list[dict],
                 timestamp: float, hash_previo: str, prueba:
                 int = 0, hash_bloque: str = None):
        """ Constructor de la clase `Bloque`.
        :param indice: ID unico del bloque.
        :param transacciones: Lista de transacciones.
        :param timestamp: Momento en que el bloque fue generado.
        :param hash_previo hash previo
        :param prueba: prueba de trabajo """

        # Codigo a completar (inicializacion de los elementos del bloque)
        self.indice = indice
        self.transacciones = transacciones
        self.timestamp = timestamp
        self.hash_previo = hash_previo
        self.prueba = prueba
        self.hash = hash_bloque

    def calcular_hash(self):
        """ Metodo que calcula el hash de un bloque """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def toDict(self):
        '''
        Método que transforma el bloque en un diccionario
        '''
        informacion = {
            'indice': self.indice,
            'transacciones': self.transacciones,
            'hash': self.hash,
            'hash_previo': self.hash_previo,
            'prueba': self.prueba,
            'timestamp': self.timestamp
        }
        return informacion


class Blockchain(object):
    def __init__(self):
        self.dificultad = 4
        self.bloques = []  # Lista de bloques encadenados
        self.primer_bloque()
        self.trans_por_hacer = []  # Transacciones por hacer

    def primer_bloque(self):
        '''
        Se crea el primer bloque con sus parámetros iniciales
        Nota -> será el mismo para todas las blockchains
        '''
        bloque = Bloque(1, [], 1, 1)
        bloque.hash = bloque.calcular_hash()
        self.bloques.append(bloque)

    def nuevo_bloque(self, hash_previo: str) -> Bloque:
        '''
        Crea un nuevo bloque a partir de
        las transacciones que no estan confirmadas

        :param prueba: el valor de prueba a insertar en el bloque
        :param hash_previo: el hash del bloque anterior de la cadena
        :return el nuevo bloque
        '''

        bloque = Bloque(len(self.bloques)+1,
                        self.trans_por_hacer, time.time(), hash_previo)

        return bloque

    def nueva_transaccion(self, origen: str, destino: str,
                          cantidad: int) -> int:
        """
        Crea una nueva transaccion a partir de un origen, un destino y una
         cantidad y la incluye en las listas de transacciones

            :param origen: <str> el que envia la transaccion
            :param destino: <str> el que recibe la transaccion
            :param cantidad: <int> la candidad 5
            :return: <int> el indice del bloque que
            va a almacenar la transaccion
        """
        # [...] Codigo a completar
        transaccion = {"origen": origen, "destino": destino,
                       "cantidad": cantidad, "tiempo": time.time()}
        self.trans_por_hacer.append(transaccion)

        # Devuelve el índice del bloque que se va
        # a crear (después del actual último)
        return len(self.bloques) + 1

    def prueba_trabajo(self, bloque: Bloque) -> str:
        """
        Algoritmo simple de prueba de trabajo:
        - Calculara el hash del bloque hasta que encuentre un
        hash que empiece por tantos ceros como dificultad.
        - Cada vez que el bloque obtenga un hash que no sea adecuado,
        incrementara en uno el campo de ``prueba del bloque''

        :param bloque: objeto de tipo bloque
        :return: el hash del nuevo bloque
        (dejará el campo de hash del bloque sin modificar)
        """
        valido = False

        while not valido:
            hash_bloque = bloque.calcular_hash()
            if hash_bloque[:self.dificultad] != "0"*self.dificultad:
                valido = False
                bloque.prueba += 1
            else:
                valido = True

        return hash_bloque

    def prueba_valida(self, bloque: Bloque, hash_bloque: str) -> bool:
        """
        Metodo que comprueba si el hash_bloque comienza con tantos
        ceros como la dificultad estipulada en el blockchain.
        Ademas comprobará que hash_bloque coincide con el valor
        devuelto del metodo de calcular hash del bloque.
        Si cualquiera de ambas comprobaciones es falsa,
        devolvera falso y en caso contrario, verdarero
        """

        valido = True

        if hash_bloque[:self.dificultad] != "0"*self.dificultad or hash_bloque != bloque.calcular_hash():
            valido = False
        return valido

    def integra_bloque(self, bloque_nuevo: Bloque, hash_prueba: str) -> bool:
        """
        Metodo para integran correctamente un bloque a la cadena de bloques.
        Debe comprobar que la prueba de hash es valida y que el hash del
        bloque ultimo de la cadena coincida con el hash_previo del bloque
        que se va a integrar. Si pasa las comprobaciones, actualiza el hash
        del bloque a integrar, lo inserta en la cadena y hace un reset de
         las transacciones no confirmadas ( vuelve a dejar la lista de
          transacciones no confirmadas a una lista vacia)

        :param bloque_nuevo: el nuevo bloque que se va a integrar
        :param hash_prueba: la prueba de hash
        :return: True si se ha podido ejecutar bien y False en caso contrario
        (si no ha pasado alguna prueba)
        """

        node = self.bloques[-1]

        if self.prueba_valida(bloque_nuevo, hash_prueba) and bloque_nuevo.hash_previo == node.hash:
            # Actualiza el hash del bloque a integrar
            bloque_nuevo.hash = hash_prueba

            self.bloques.append(bloque_nuevo)
            return True
        else:
            return False


if __name__ == "__main__":

    pass
