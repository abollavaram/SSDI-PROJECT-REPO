import logging
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from base.models import Product, Order, OrderItem, ShippingAddress
from base.serializers import OrderSerializer

# Set up a logger
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addOrderItems(request):
    user = request.user
    data = request.data

    print("Incoming order data:", data)  # Debugging: print incoming data

    try:
        # Validate that order items are present
        orderItems = data.get('orderItems', [])
        if not orderItems:
            return Response({'detail': 'No Order Items'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the order
        order = Order.objects.create(
            user=user,
            paymentMethod=data['paymentMethod'],
            taxPrice=data['taxPrice'],
            shippingPrice=data['shippingPrice'],
            totalPrice=data['totalPrice'],
            createdAt=datetime.now()  # Ensure createdAt is populated
        )
        print("Order created with ID:", order._id)

        # Create the shipping address
        shipping = ShippingAddress.objects.create(
            order=order,
            address=data['shippingAddress']['address'],
            city=data['shippingAddress']['city'],
            postalCode=data['shippingAddress']['postalCode'],
            country=data['shippingAddress']['country'],
        )
        print("Shipping address created for order ID:", order._id)

        # Create order items and update stock
        for i in orderItems:
            product = Product.objects.get(_id=i['product'])
            print("Processing product:", product.name)

            OrderItem.objects.create(
                product=product,
                order=order,
                name=product.name,
                qty=i['qty'],
                price=i['price'],
                image=product.image.url,
            )
            print(f"Order item created for product {product.name}")

            # Update stock
            product.countInStock -= i['qty']
            product.save()
            print(f"Stock updated for {product.name}, new stock: {product.countInStock}")

        serializer = OrderSerializer(order, many=False)
        return Response(serializer.data)

    except Product.DoesNotExist as e:
        print("Product not found:", str(e))
        return Response({'detail': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print("Unexpected error:", str(e))
        return Response({'detail': 'An unexpected error occurred', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getMyOrders(request):
    user = request.user
    try:
        orders = user.order_set.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Failed to retrieve user orders: {str(e)}")
        return Response({'detail': 'Failed to retrieve user orders'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def getOrders(request):
    try:
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Failed to retrieve all orders: {str(e)}")
        return Response({'detail': 'Failed to retrieve all orders'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getOrderById(request, pk):
    user = request.user
    try:
        order = Order.objects.get(_id=pk)
        if user.is_staff or order.user == user:
            serializer = OrderSerializer(order, many=False)
            return Response(serializer.data)
        else:
            return Response({'detail': 'Not authorized to view this order'}, status=status.HTTP_403_FORBIDDEN)
    except Order.DoesNotExist:
        logger.error("Order not found")
        return Response({'detail': 'Order does not exist'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return Response({'detail': 'An error occurred', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateOrderToPaid(request, pk):
    try:
        order = Order.objects.get(_id=pk)

        order.isPaid = True
        order.paidAt = datetime.now()
        order.save()

        return Response({'detail': 'Order was paid'})
    except Order.DoesNotExist:
        logger.error("Order not found")
        return Response({'detail': 'Order does not exist'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return Response({'detail': 'An error occurred', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToDelivered(request, pk):
    try:
        order = Order.objects.get(_id=pk)

        order.isDelivered = True
        order.deliveredAt = datetime.now()
        order.save()

        return Response({'detail': 'Order was delivered'})
    except Order.DoesNotExist:
        logger.error("Order not found")
        return Response({'detail': 'Order does not exist'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return Response({'detail': 'An error occurred', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
