#!/bin/bash
echo "========================================"
echo "  ����� ê�� �鿣�� ����"
echo "========================================"
echo ""

# Python Ȯ��
if ! command -v python &> /dev/null; then
    echo "[ERROR] Python�� ��ġ�Ǿ� ���� �ʽ��ϴ�!"
    echo "Python 3.8 �̻��� ��ġ���ּ���."
    exit 1
fi

echo "[1/3] ������ Ȯ�� �� ��ġ..."
pip install -q -r requirements.txt

echo "[2/3] ���� ���� ��..."
echo ""
echo "** ù ����� �� �ٿ�ε�� 5-10�� �ҿ�� �� �ֽ��ϴ� **"
echo ""

echo "[3/3] API ���� ����..."
python api/server.py
