inp = input().split()
cuenta =  int(inp[1])

for i in range(int(inp[2])  + 1):
    
    valor = int(inp[0]) * i
    cuenta -= valor
    if cuenta > 0:
        prestado = 0
    else:
        prestado = -cuenta 
print(prestado)
    

